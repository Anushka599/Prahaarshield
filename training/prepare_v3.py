"""PrahaarShield v3 data preparation (laptop, ~1 minute, no GPU).

Put next to: scam_dataset.jsonl, benign_dataset*.jsonl, hard_negatives_dataset.jsonl
Optional:    prahaar_feedback.csv   (downloaded from the testing UI: ⬇ button)  -> your corrections become training rows
             review_decisions.csv   (your decisions on review_queue.csv)        -> applied to the labels

Run:  python prepare_v3.py
Out:  prepared_v3/train.jsonl val.jsonl test.jsonl   (split by SIMILARITY GROUP: near-duplicates never cross splits)
      prepared_v3/review_queue.csv                   (top ~100 rows whose label looks wrong -> fill the 'decision' column,
                                                       save as review_decisions.csv next to this script, run again)
      prepared_v3/report.txt
Decisions: keep | scam | benign | type:<scam_type> | drop
"""
import csv, glob, hashlib, json, os, random, re
from collections import Counter, defaultdict

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "prepared_v3")
SEED = 2026
TYPES = ["digital_arrest", "kyc_bank", "boss_impersonation", "investment_group", "job_task", "loan_app"]
PILLARS = ["P_IDENTITY", "P_SITUATION", "P_STAKES", "P_CRED", "P_RESOURCE", "P_CONTROL"]
DEV, LAT = re.compile(r"[\u0900-\u097F]"), re.compile(r"[A-Za-z]")
SIM_THRESHOLD = 0.60     # char-ngram cosine above this -> same group (paraphrase siblings)
# UI leftovers from the old v2 export: they never appear in real WhatsApp text, and they occurred ONLY in benign rows
BTN = re.compile(r"\[\s*Button\s*:[^\]]*\]", re.I)
META = re.compile(r"(?:\b(?:hi|hello|hey|dear)\s+|नमस्ते\s+)?\bmeta\s*ai\b[\s,:!-]*", re.I)
CLEANED = Counter()


def clean_artifacts(t):
    t2 = BTN.sub(" ", t)
    if t2 != t: CLEANED["button_markup"] += 1
    t3 = META.sub("", t2)
    if t3 != t2: CLEANED["meta_ai"] += 1
    return re.sub(r"[ \t]{2,}", " ", t3).strip()


def lang_of(lang, text):
    if lang in ("en", "hinglish", "hi_deva", "mr", "other"):
        return lang
    if lang == "hi":
        return "hi_deva" if len(DEV.findall(text)) >= len(LAT.findall(text)) else "hinglish"
    return "hi_deva" if len(DEV.findall(text)) > len(LAT.findall(text)) else "en"


def rid(text):
    return "r" + hashlib.md5(text.strip().encode("utf-8")).hexdigest()[:10]


def load_rows():
    rows, seen = [], set()
    files = sorted(f for f in glob.glob(os.path.join(HERE, "*.jsonl")))
    for f in files:
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            r = json.loads(line)
            t = clean_artifacts((r.get("text") or "").strip())
            if not t or t in seen:
                continue
            seen.add(t)
            is_scam = int(r.get("is_scam", 0))
            st = r.get("scam_type") if is_scam else "benign"
            if is_scam and st not in TYPES:
                st = {"kyc_phishing": "kyc_bank"}.get(st, st)
            pl = r.get("pillar_labels", r.get("pillars", []))
            rows.append({"id": rid(t), "text": t, "is_scam": is_scam, "scam_type": st, "pillar_labels": (None if ("pillar_labels" in r and r["pillar_labels"] is None) else [p for p in (pl or []) if p in PILLARS]),
                         "role": r.get("role") or "none", "language": lang_of(r.get("language"), t), "category": str(r.get("category") or ""),
                         "source": os.path.basename(f)})
    return rows, files


def load_feedback(seen_texts):
    path = os.path.join(HERE, "prahaar_feedback.csv")
    if not os.path.exists(path):
        return []
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        t = (r.get("text") or "").strip()
        if not t or t in seen_texts or t.startswith("["):
            continue
        is_scam = 1 if r.get("expected") == "scam" else 0
        note = (r.get("note") or "").lower()
        st = next((x for x in TYPES if x in note or x.split("_")[0] in note), r.get("model_type")) if is_scam else "benign"
        out.append({"id": rid(t), "text": t, "is_scam": is_scam, "scam_type": st if (not is_scam or st in TYPES) else "kyc_bank",
                    "pillar_labels": None,                       # unknown -> pillar loss masked for this row
                    "role": "none", "language": lang_of(r.get("language"), t), "category": "ui_feedback", "source": "prahaar_feedback.csv"})
        seen_texts.add(t)
    return out


def apply_decisions(rows):
    path = os.path.join(HERE, "review_decisions.csv")
    if not os.path.exists(path):
        return rows, Counter()
    dec = {r["id"]: (r.get("decision") or "").strip().lower() for r in csv.DictReader(open(path, encoding="utf-8"))}
    stats, out = Counter(), []
    for r in rows:
        d = dec.get(r["id"], "")
        if d == "drop":
            stats["dropped"] += 1
            continue
        if d == "scam" and not r["is_scam"]:
            r.update(is_scam=1, scam_type="kyc_bank", pillar_labels=None); stats["to_scam"] += 1
        elif d == "benign" and r["is_scam"]:
            r.update(is_scam=0, scam_type="benign", pillar_labels=[]); stats["to_benign"] += 1
        elif d.startswith("type:") and d[5:] in TYPES:
            r.update(is_scam=1, scam_type=d[5:]); stats["type_changed"] += 1
        out.append(r)
    return out, stats


def holdout_selftest(rows):
    """Remove training rows that are near-copies of the self-test cases, so the self-test stays a fair test."""
    for cand in (os.path.join(HERE, "selftest_cases.json"), os.path.join(HERE, "..", "app", "eval", "selftest_cases.json")):
        if os.path.exists(cand):
            cases = [c["text"] for c in json.load(open(cand, encoding="utf-8"))]
            break
    else:
        return rows, 0
    texts = [re.sub(r"\s+", " ", r["text"].lower()) for r in rows] + [re.sub(r"\s+", " ", c.lower()) for c in cases]
    X = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True).fit_transform(texts)
    S = (X[:len(rows)] @ X[len(rows):].T).tocsr()
    bad = {i for i in range(len(rows)) if S.getrow(i).nnz and S.getrow(i).data.max() >= 0.80}
    return [r for i, r in enumerate(rows) if i not in bad], len(bad)


def similarity_groups(rows):
    texts = [re.sub(r"\s+", " ", r["text"].lower()) for r in rows]
    X = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True).fit_transform(texts)
    S = (X @ X.T).tocsr()
    parent = list(range(len(rows)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(len(rows)):
        row = S.getrow(i)
        for j, v in zip(row.indices, row.data):
            if j > i and v >= SIM_THRESHOLD:
                parent[find(i)] = find(j)
    return [find(i) for i in range(len(rows))]


def group_split(rows, groups):
    rnd = random.Random(SEED)
    by_group = defaultdict(list)
    for r, g in zip(rows, groups):
        by_group[g].append(r)
    strata = defaultdict(list)
    for g, rs in by_group.items():
        key = Counter((r["is_scam"], r["scam_type"]) for r in rs).most_common(1)[0][0]
        strata[key].append(g)
    split = {}
    for key, gs in strata.items():
        rnd.shuffle(gs)
        n = sum(len(by_group[g]) for g in gs)
        cnt = {"test": 0, "val": 0}
        for g in gs:
            size = len(by_group[g])
            if any(r["source"] == "prahaar_feedback.csv" for r in by_group[g]):
                split[g] = "train"
            elif cnt["test"] < 0.10 * n:
                split[g] = "test"; cnt["test"] += size
            elif cnt["val"] < 0.10 * n:
                split[g] = "val"; cnt["val"] += size
            else:
                split[g] = "train"
    for r, g in zip(rows, groups):
        r["group"] = f"g{g}"
        r["split"] = split[g]
    return rows


def review_queue(rows):
    """5-fold TF-IDF out-of-fold predictions: rows where an independent model strongly disagrees with the label."""
    texts = [r["text"] for r in rows]
    y = np.array([r["is_scam"] for r in rows])
    oof = np.zeros(len(rows))
    oof_type = [""] * len(rows)
    oof_type_p = np.zeros(len(rows))
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    for tr, te in skf.split(texts, y):
        wv = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        cv = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=150000)
        Xtr = hstack([wv.fit_transform([texts[i] for i in tr]), cv.fit_transform([texts[i] for i in tr])])
        Xte = hstack([wv.transform([texts[i] for i in te]), cv.transform([texts[i] for i in te])])
        clf = LogisticRegression(max_iter=3000, class_weight="balanced").fit(Xtr, y[tr])
        oof[te] = clf.predict_proba(Xte)[:, 1]
        sc = [i for i in tr if rows[i]["is_scam"]]
        tclf = LogisticRegression(max_iter=3000, class_weight="balanced").fit(Xtr.tocsr()[[list(tr).index(i) for i in sc]], [rows[i]["scam_type"] for i in sc])
        P = tclf.predict_proba(Xte)
        for k, i in enumerate(te):
            j = int(P[k].argmax()); oof_type[i] = tclf.classes_[j]; oof_type_p[i] = P[k, j]
    flagged = []
    for i, r in enumerate(rows):
        if r["is_scam"] == 1 and oof[i] < 0.5:
            flagged.append((1 - oof[i], i, "looks BENIGN"))
        elif r["is_scam"] == 0 and oof[i] > 0.5:
            flagged.append((oof[i], i, "looks SCAM"))
        elif r["is_scam"] == 1 and oof_type[i] != r["scam_type"] and oof_type_p[i] > 0.60:
            flagged.append((oof_type_p[i] * 0.9, i, f"looks like {oof_type[i]}"))
    flagged.sort(reverse=True)
    return [(rows[i], oof[i], oof_type[i], why) for _, i, why in flagged[:100]]


def main():
    rows, files = load_rows()
    fb = load_feedback({r["text"] for r in rows})
    rows += fb
    rows, dstats = apply_decisions(rows)
    rows, n_held = holdout_selftest(rows)
    groups = similarity_groups(rows)
    rows = group_split(rows, groups)
    os.makedirs(OUT, exist_ok=True)
    for s in ("train", "val", "test"):
        with open(os.path.join(OUT, f"{s}.jsonl"), "w", encoding="utf-8") as f:
            for r in random.Random(SEED + len(s)).sample([x for x in rows if x["split"] == s], k=sum(1 for x in rows if x["split"] == s)):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    q = review_queue([r for r in rows if r["source"] != "prahaar_feedback.csv"])
    with open(os.path.join(OUT, "review_queue.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "split", "text", "is_scam", "scam_type", "independent_p_scam", "independent_type", "why_flagged", "decision"])
        for r, p, t, why in q:
            w.writerow([r["id"], r["split"], r["text"], r["is_scam"], r["scam_type"], round(float(p), 3), t, why, ""])
    sp = Counter(r["split"] for r in rows)
    lines = [f"files: {[os.path.basename(f) for f in files]}", f"rows: {len(rows)}  (feedback rows added: {len(fb)})  decisions applied: {dict(dstats)}",
             f"artifacts cleaned: {dict(CLEANED)}  | removed as near-copies of self-test cases: {n_held}",
             f"similarity groups: {len(set(groups))}  (rows sharing a group with another row: {sum(1 for g, c in Counter(groups).items() if c > 1 for _ in range(c))})",
             "split: " + "  ".join(f"{s}={sp[s]} (scam {sum(1 for r in rows if r['split']==s and r['is_scam'])})" for s in ('train', 'val', 'test')),
             "scam types: " + str(dict(Counter(r['scam_type'] for r in rows))), "languages: " + str(dict(Counter(r['language'] for r in rows))),
             f"review queue: {len(q)} rows -> prepared_v3/review_queue.csv"]
    open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
