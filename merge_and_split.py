"""PrahaarShield - Step 1: merge ALL dataset files and split train / val / test.

Put this file in C:\\PRahaarshield_Miniproject (same folder as your .jsonl files) and run:
    python merge_and_split.py

- Reads every .jsonl file in this folder (and sub-folders), except the 'prepared' folder.
- Keeps rows AS THEY ARE. Only maps them into the same 7 fields:
    text, is_scam, scam_type, pillar_labels, role, language, category
- Removes only EXACT duplicate texts (the same message present in two files, e.g. twins file + benign_dataset).
- Stratified split by (is_scam, scam_type): 80% train / 10% val / 10% test, fixed seed.
Output: prepared/merged.jsonl, prepared/train.jsonl, prepared/val.jsonl, prepared/test.jsonl, prepared/report.txt
"""
import glob, json, os, random, re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "prepared")
PILLARS = ["P_IDENTITY", "P_SITUATION", "P_STAKES", "P_CRED", "P_RESOURCE", "P_CONTROL"]
CAT2TYPE = {"digital_arrest": "digital_arrest", "kyc_phishing": "kyc_bank"}
DEV, LAT = re.compile(r"[\u0900-\u097F]"), re.compile(r"[A-Za-z]")


def language(lang, text):
    lang = (lang or "").strip()
    if lang in ("en", "hinglish", "hi_deva", "mr", "other"):
        return lang
    if lang == "hi":
        return "hi_deva" if len(DEV.findall(text)) >= len(LAT.findall(text)) else "hinglish"
    return "hi_deva" if len(DEV.findall(text)) > len(LAT.findall(text)) else "en"


def pillars(r):
    p = r.get("pillar_labels", r.get("pillars", [])) or []
    if p and all(isinstance(x, (int, float)) for x in p):          # 0/1 vector -> names
        return [PILLARS[i] for i, v in enumerate(p) if v]
    return [x for x in p if x in PILLARS]


def to_row(r):
    text = r.get("text") or r.get("message_text") or ""
    if not text.strip():
        return None
    is_scam = int(r.get("is_scam", r.get("label", 0)))
    st = r.get("scam_type")
    if not st:
        st = CAT2TYPE.get(r.get("category"), "other_scam") if is_scam else "benign"
    if not is_scam:
        st = "benign"
    cat = (r.get("hard_negative_type") or r.get("step_or_subtopic") or r.get("benign_subtype")
           or r.get("category") or "")
    return {"text": text, "is_scam": is_scam, "scam_type": st, "pillar_labels": pillars(r),
            "role": r.get("role") or "none", "language": language(r.get("language"), text), "category": str(cat)}


def main():
    files = [f for f in glob.glob(os.path.join(HERE, "**", "*.jsonl"), recursive=True)
             if os.sep + "prepared" + os.sep not in f]
    rows, seen, per_file, dups = [], set(), Counter(), 0
    for f in sorted(files):
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            row = to_row(json.loads(line))
            if row is None:
                continue
            key = row["text"].strip()
            if key in seen:
                dups += 1
                continue
            seen.add(key)
            rows.append(row)
            per_file[os.path.basename(f)] += 1
    # stratified 80/10/10
    rnd = random.Random(2026)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["is_scam"], r["scam_type"])].append(r)
    split = {"train": [], "val": [], "test": []}
    for g in groups.values():
        rnd.shuffle(g)
        n = len(g); nv = max(1, round(n * 0.1)) if n >= 10 else 0; nt = nv
        split["val"] += g[:nv]; split["test"] += g[nv:nv + nt]; split["train"] += g[nv + nt:]
    os.makedirs(OUT, exist_ok=True)
    for name, data in [("merged", rows)] + list(split.items()):
        rnd.shuffle(data)
        with open(os.path.join(OUT, f"{name}.jsonl"), "w", encoding="utf-8") as fh:
            for r in data:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    L = [f"files read: {len(files)}   rows kept: {len(rows)}   exact duplicates skipped: {dups}", "", "rows per file:"]
    L += [f"  {k:45s} {v}" for k, v in sorted(per_file.items())]
    L += ["", f"scam={sum(r['is_scam'] for r in rows)}  benign={sum(1 - r['is_scam'] for r in rows)}", "", "scam_type:"]
    L += [f"  {k:22s} {v}" for k, v in Counter(r["scam_type"] for r in rows).most_common()]
    L += ["", "language: " + str(dict(Counter(r["language"] for r in rows)))]
    L += ["", "split: " + "  ".join(f"{k}={len(v)} (scam {sum(r['is_scam'] for r in v)})" for k, v in split.items())]
    rep = "\n".join(L)
    open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8").write(rep)
    print(rep)


if __name__ == "__main__":
    main()
