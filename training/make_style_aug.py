"""Create style-varied copies of the training data (same probability for scam and benign).   python make_style_aug.py
Writes style_aug_v33.jsonl here; prepare_v3.py picks it up. Near-duplicate copies stay in the SAME split as their original
(prepare_v3 groups similar texts), so no test leakage."""
import glob, json, os, random, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style_augment import random_profile, stylize
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "style_aug_v33.jsonl"); RATE = 0.35
import csv
DROP = set()
dec = os.path.join(HERE, "review_decisions.csv")
if os.path.exists(dec):                                    # rows dropped in the label review must not come back as style copies
    DROP = {r["text"].strip() for r in csv.DictReader(open(dec, encoding="utf-8")) if r.get("decision", "").strip().lower() == "drop"}
rng = random.Random(2026); rows, seen = [], set()
for f in sorted(glob.glob(os.path.join(HERE, "*.jsonl"))):
    if os.path.basename(f) == "style_aug_v33.jsonl": continue
    for line in open(f, encoding="utf-8"):
        r = json.loads(line); t = (r.get("text") or "").strip()
        if t and t not in seen and t not in DROP: seen.add(t); rows.append(r)
out, prof = [], Counter()
for r in rows:
    if rng.random() >= RATE: continue                       # same rate for every label
    p = random_profile(rng); new = stylize(r["text"], r.get("language", "en"), p, rng)
    if new == r["text"] or new in seen: continue
    seen.add(new); prof[(p, r["is_scam"])] += 1
    out.append({**r, "text": new, "category": f"style_v33:{p}:{r.get('category', '')}"})
with open(OUT, "w", encoding="utf-8") as fh:
    for r in out: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
sc = sum(r["is_scam"] for r in out)
print(f"source rows {len(rows)} -> style copies {len(out)} (scam {sc}, benign {len(out) - sc}) -> {os.path.basename(OUT)}")
print("profiles (scam share):", {p: f"{prof[(p,1)]}/{prof[(p,0)] + prof[(p,1)]}" for p in sorted({k[0] for k in prof})})
