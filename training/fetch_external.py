"""Download the public Ridham115/indian-scam-sms-synthetic-audited dataset (CC BY 4.0) and map it to our 7-field schema.
   python fetch_external.py                 (downloads via the Hugging Face datasets-server API, no extra packages)
   python fetch_external.py --csv file.csv  (if you downloaded the CSV yourself from the dataset's "Files" tab)
Kept: languages en / hinglish / hi / mr_en  (Tamil, Telugu, Bengali code-mix dropped: outside our 4 languages)
Kept scam types (financial, our 6): fake_kyc, fake_bank_otp, electricity_bill -> kyc_bank | loan_offer -> loan_app | job_offer -> job_task
lottery, courier_customs -> other_scam (still financial scams: the model learns them as scam; the type head skips them).
Dropped scam rows: unknown (rows flipped to scam during the audit: ambiguous).  ALL safe rows are kept (genuine look-alikes).
Pillar labels are unknown for these rows -> stored as null so the pillar loss skips them.
"""
import csv, json, sys, time, urllib.request
from pathlib import Path
HERE = Path(__file__).resolve().parent
DS = "Ridham115/indian-scam-sms-synthetic-audited"
LANG = {"en": "en", "hinglish": "hinglish", "hi": "hi_deva", "mr_en": "mr"}
TYPE = {"fake_kyc": "kyc_bank", "fake_bank_otp": "kyc_bank", "electricity_bill": "kyc_bank", "loan_offer": "loan_app", "job_offer": "job_task",
        "lottery": "other_scam", "courier_customs": "other_scam"}   # financial scams outside our 6 types: learned as SCAM, type head skips them

def rows_api():
    out, off = [], 0
    while True:
        url = f"https://datasets-server.huggingface.co/rows?dataset={DS}&config=default&split=train&offset={off}&length=100"
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    data = json.loads(r.read().decode("utf-8")); break
            except Exception as e:
                print("  retry", attempt + 1, e); time.sleep(3)
        else:
            sys.exit("Could not reach Hugging Face. Download the CSV from the dataset page (Files tab) and run: python fetch_external.py --csv <file>")
        batch = [x["row"] for x in data.get("rows", [])]
        out += batch; off += len(batch)
        if not batch or off >= data.get("num_rows_total", 0): return out

def main():
    src = rows_api() if "--csv" not in sys.argv else list(csv.DictReader(open(sys.argv[sys.argv.index("--csv") + 1], encoding="utf-8")))
    keep, drop = [], {}
    for r in src:
        lang = LANG.get(r.get("language"))
        if not lang:
            drop["other_language"] = drop.get("other_language", 0) + 1; continue
        if r.get("label") == "scam":
            st = TYPE.get(r.get("scam_type"))
            if not st:
                drop["scam_type_" + str(r.get("scam_type"))] = drop.get("scam_type_" + str(r.get("scam_type")), 0) + 1; continue
            keep.append({"text": r["text"], "is_scam": 1, "scam_type": st, "pillar_labels": None, "role": "none", "language": lang, "category": "ext_ridham:" + r.get("topic", "")})
        else:
            keep.append({"text": r["text"], "is_scam": 0, "scam_type": "benign", "pillar_labels": None, "role": "none", "language": lang, "category": "ext_ridham:" + r.get("topic", "")})
    with open(HERE / "ext_ridham.jsonl", "w", encoding="utf-8") as f:
        for r in keep: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"downloaded {len(src)} rows -> kept {len(keep)} (scam {sum(r['is_scam'] for r in keep)}, safe {sum(1 - r['is_scam'] for r in keep)}) -> ext_ridham.jsonl")
    print("dropped:", drop)

if __name__ == "__main__":
    main()
