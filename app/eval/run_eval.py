"""PrahaarShield v3 – full evaluation (laptop, real model; ~5-10 min on CPU).

Run from the app folder:   python -m eval.run_eval --data ..\\training
  (--data = folder that contains prepared_v3\\ and conversations\\ from prepare_v3.py / build_conversations.py)
Writes eval/eval_report.md + eval/eval_results.json  -> send both to Claude.

Sections: 1 messages (test split, per language, calibration)  2 tricks (adversarial)  3 identifiers
          4 conversations through the FULL system (engine + M7 + Brain), streamed message by message   5 speed
"""
import argparse, json, random, statistics, time
from collections import Counter, defaultdict
from pathlib import Path

from brain.brain import assess_chat, message_level
from engine.conversation import load_conv
from engine.identifiers import check_link, check_phone, check_upi
from engine.text_engine import find_model_dir, load_engine
from eval.tricks import TRICKS

HERE = Path(__file__).resolve().parent


def f1(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def binary_metrics(y, pred):
    tp = sum(1 for a, b in zip(y, pred) if a and b); fp = sum(1 for a, b in zip(y, pred) if not a and b)
    fn = sum(1 for a, b in zip(y, pred) if a and not b); tn = sum(1 for a, b in zip(y, pred) if not a and not b)
    p, r, f = f1(tp, fp, fn); pn, rn, fnn = f1(tn, fn, fp)
    return {"n": len(y), "scam_precision": round(p, 4), "scam_recall": round(r, 4), "scam_f1": round(f, 4), "macro_f1": round((f + fnn) / 2, 4),
            "false_alarm_rate": round(fp / max(1, fp + tn), 4), "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}}


def ece(ps, ys, bins=10):
    e = 0.0
    for b in range(bins):
        idx = [i for i, p in enumerate(ps) if (b / bins <= p < (b + 1) / bins) or (b == bins - 1 and p == 1.0)]
        if idx:
            e += len(idx) / len(ps) * abs(statistics.mean(ps[i] for i in idx) - statistics.mean(ys[i] for i in idx))
    return round(e, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE.parents[1] / "training"))
    ap.add_argument("--quick", action="store_true", help="smaller samples (for a fast check)")
    args = ap.parse_args()
    data = Path(args.data)
    eng = load_engine()
    try:
        conv = load_conv(None if hasattr(eng, "CUES") else find_model_dir())
    except FileNotFoundError:
        conv = load_conv(None)
    th = float(getattr(eng, "threshold", 0.5))
    R, rnd, t_all = {}, random.Random(2026), time.time()

    # 1 ---------------- messages
    test = [json.loads(l) for l in open(data / "prepared_v3" / "test.jsonl", encoding="utf-8")]
    if args.quick:
        test = rnd.sample(test, min(80, len(test)))
    times, res = [], []
    for r in test:
        t0 = time.time(); a = eng.analyze(r["text"]); times.append((time.time() - t0) * 1000)
        res.append((r, a, message_level(a, th) >= 2))
    y = [r["is_scam"] for r, _, _ in res]
    R["messages"] = binary_metrics(y, [p for _, _, p in res])
    R["messages"]["ece"] = ece([a["p_scam"] for _, a, _ in res], y)
    per = defaultdict(lambda: ([], []))
    for r, a, p in res:
        per[r["language"]][0].append(r["is_scam"]); per[r["language"]][1].append(p)
    R["messages_per_language"] = {l: binary_metrics(a, b) | {"n": len(a)} for l, (a, b) in per.items() if len(a) >= 10}
    sc = [(r, a) for r, a, _ in res if r["is_scam"]]
    R["scam_type_accuracy"] = round(sum(a["scam_type"] == r["scam_type"] for r, a in sc) / max(1, len(sc)), 4)
    R["message_errors"] = [{"text": r["text"][:160], "true": r["is_scam"], "p": a["p_scam"], "type": a["scam_type"], "lang": r["language"]}
                           for r, a, p in res if p != bool(r["is_scam"])][:40]

    # 2 ---------------- tricks
    base = [r for r, _, _ in res]
    sample = rnd.sample(base, min(len(base), 60 if args.quick else 160))
    R["tricks"] = {}
    for name, fn in TRICKS.items():
        ys, ps = [], []
        for r in sample:
            a = eng.analyze(fn(r["text"], rnd)); ys.append(r["is_scam"]); ps.append(message_level(a, th) >= 2)
        R["tricks"][name] = binary_metrics(ys, ps)
    pred_by_id = {r["id"]: p for r, _, p in res}
    clean = binary_metrics([r["is_scam"] for r in sample], [pred_by_id[r["id"]] for r in sample])
    R["tricks"]["_clean_same_sample"] = clean

    # 3 ---------------- identifiers
    F = {"link": check_link, "upi": check_upi, "phone": check_phone}
    cases = json.load(open(HERE / "identifier_tests.json", encoding="utf-8"))
    tp = fp = fn = tn = notes_ok = notes = 0
    for c in cases:
        r = F[c["kind"]](c["value"], c.get("text", "")); flagged = r["risk"] in ("registry_hit", "suspicious")
        if c["expected"] == "bad": tp += flagged; fn += not flagged
        elif c["expected"] == "good": fp += flagged; tn += not flagged
        else: notes += 1; notes_ok += (r["risk"] == "note")
    p, rr, ff = f1(tp, fp, fn)
    R["identifiers"] = {"n": len(cases), "precision": round(p, 4), "recall": round(rr, 4), "f1": round(ff, 4), "false_flags_on_genuine": fp,
                        "notes_correct": f"{notes_ok}/{notes}", "caveat": "test cases were written by the developers; real-world rates will be lower"}

    # 4 ---------------- conversations through the full system
    chats = [json.loads(l) for l in open(data / "conversations" / "conv_test.jsonl", encoding="utf-8")]
    if args.quick:
        chats = rnd.sample(chats, min(40, len(chats)))
    cache = {}
    def feats(text, direction):
        k = (text, direction)
        if k not in cache:
            cache[k] = eng.analyze_full(text) if direction == "in" else (None, eng.features(text))
        return cache[k]
    agg = defaultdict(Counter)
    for ch in chats:
        msgs, items, max_level, first_alert, turn, demand_at = [], [], 0, None, None, None
        for i, m in enumerate(ch["messages"]):
            d = "in" if m["speaker"] == "them" else "out"
            a, fe = feats(m["text"], d)
            msgs.append({"id": str(i), "direction": d, "text": m["text"], "analysis": a})
            items.append({"vec": fe["vec"], "raw": fe["raw"], "speaker": "them" if d == "in" else "me"})
            if d == "in":
                cv = conv.predict(items) if conv else None
                lvl = assess_chat(msgs, th, None, cv)["level"]
                max_level = max(max_level, lvl)
                if lvl >= 3 and first_alert is None: first_alert = i
                if m.get("is_scam_msg") and turn is None: turn = i
                if m.get("stage") == "demand" and demand_at is None: demand_at = i
        kind = ch["kind"]; src = ch.get("source", "assembled")
        for key in (kind, f"{kind}|{src}"):
            g = agg[key]; g["chats"] += 1
            g["reached_L3+"] += max_level >= 3; g["reached_L4"] += max_level >= 4
            if kind == "slow_burn" and first_alert is not None and turn is not None and first_alert < turn: g["alert_before_turn"] += 1
            if demand_at is not None: g["has_demand"] += 1
    R["conversations"] = {}
    for key, g in agg.items():
        n = g["chats"]
        if key.startswith("benign"):
            R["conversations"][key] = {"chats": n, "false_alarm_L3+": round(g["reached_L3+"] / n, 4)}
        else:
            R["conversations"][key] = {"chats": n, "detected_L3+": round(g["reached_L3+"] / n, 4), "critical_L4": round(g["reached_L4"] / n, 4),
                                       **({"alert_before_turning_point": round(g["alert_before_turn"] / n, 4)} if key.startswith("slow") else {})}
    R["conversation_model"] = type(conv).__name__ if conv else "rules only"

    # 5 ---------------- speed
    R["speed_ms_per_message"] = {"median": round(statistics.median(times), 1), "p95": round(sorted(times)[int(0.95 * len(times)) - 1], 1)}
    R["engine"] = type(eng).__name__; R["threshold"] = th; R["total_minutes"] = round((time.time() - t_all) / 60, 1)
    json.dump(R, open(HERE / "eval_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_report(R)
    print(open(HERE / "eval_report.md", encoding="utf-8").read())


def write_report(R):
    m = R["messages"]
    L = ["# PrahaarShield v3 – evaluation report", "", f"Engine: {R['engine']} · conversation: {R['conversation_model']} · threshold {R['threshold']}", "",
         "## 1. Messages (test split)", "", "| Metric | Value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in m.items() if k != "confusion"] + [f"| confusion | {m['confusion']} |", f"| scam-type accuracy | {R['scam_type_accuracy']} |", ""]
    L += ["### Per language", "", "| Language | n | Macro-F1 | Scam recall | False alarms |", "|---|---|---|---|---|"]
    L += [f"| {l} | {v['n']} | {v['macro_f1']} | {v['scam_recall']} | {v['false_alarm_rate']} |" for l, v in R["messages_per_language"].items()]
    L += ["", "## 2. Tricks (same sample, each trick applied to every message)", "", "| Trick | Scam recall | False alarms | Macro-F1 |", "|---|---|---|---|"]
    L += [f"| {k} | {v['scam_recall']} | {v['false_alarm_rate']} | {v['macro_f1']} |" for k, v in R["tricks"].items()]
    i = R["identifiers"]
    L += ["", "## 3. Identifier checks", "", f"{i['n']} cases · precision {i['precision']} · recall {i['recall']} · F1 {i['f1']} · false flags on genuine {i['false_flags_on_genuine']} · notes correct {i['notes_correct']}",
          f"_Caveat: {i['caveat']}._", "", "## 4. Conversations (full system, streamed message by message)", "", "| Group | Result |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(R["conversations"].items())]
    L += ["", "## 5. Speed (laptop CPU)", "", f"median {R['speed_ms_per_message']['median']} ms · p95 {R['speed_ms_per_message']['p95']} ms per message", "",
          f"_Total run time {R['total_minutes']} min._"]
    open(HERE / "eval_report.md", "w", encoding="utf-8").write("\n".join(L))


if __name__ == "__main__":
    main()
