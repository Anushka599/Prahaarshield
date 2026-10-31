# PrahaarShield Text Engine v3 – what to do, in order

Folder layout on your laptop:
```
C:\PRahaarshield_Miniproject\
   models\        <- muril_multitask.pt, muril_multitask_tokenizer\, muril_multitask_config.json  (v2 now, v3 later)
   app\           <- from this zip (replace the old app folder)
   training\      <- from this zip
```

## STEP 1 – Install the two new packages (2 min)
```
cd C:\PRahaarshield_Miniproject\app
pip install -r requirements.txt
```

## STEP 2 – Test the v2 model in the new UI (today, 1–2 h)  ← testing that was pending
```
python check_model.py          (6 lines: 4 scam lines risky, 2 normal Safe)
run_app.bat                    -> open http://localhost:8000/sim
```
1. The setup wizard opens: language → account type → name + single/group → contacts permission → safe/blocked/not saved → number.
   (⚙ sliders icon on the right header re-opens it.)
2. Type as the scammer on the right, as the user on the left. Use TESTING_GUIDE rounds + try different setups
   (Scam account, Blocked number, Safe contact, +92 number, Business named "Fresh Mart" claiming to be SBI, a group).
3. Mark mistakes with **✗ wrong** (+ note, e.g. the right scam type). Download the CSV with ⬇ → save as
   `training\prahaar_feedback.csv`.
4. Check `http://localhost:8000/api/info` shows engine TextEngine and your threshold.

## STEP 3 – Prepare v3 data (laptop, 5 min + ~30 min review)
Copy `scam_dataset.jsonl`, `benign_dataset_FINAL.jsonl`, `hard_negatives_dataset.jsonl` into `training\` (only these 3 .jsonl files).
```
cd C:\PRahaarshield_Miniproject\training
python prepare_v3.py
```
- Open `prepared_v3\review_queue.csv` (100 rows). In the **decision** column write: `keep`, `scam`, `benign`, `type:<scam_type>` or `drop`.
- Save it as `training\review_decisions.csv`, then run again:
```
python prepare_v3.py
python build_conversations.py
```

## STEP 4 – Train on Colab (~1 h)
Google Drive `MyDrive/PrahaarShield/`:
- `prepared_v3/` ← train.jsonl, val.jsonl, test.jsonl
- `conversations/` ← conv_train.jsonl, conv_val.jsonl, conv_test.jsonl
- `code/` ← `app\engine` and `app\common` folders (replace the old ones)

Open `training\train_v3.ipynb` in Colab → T4 GPU → Run all. **Copy the SUMMARY output to Claude.**

## STEP 5 – Use the v3 models
From `MyDrive/PrahaarShield/models_v3/` download into `C:\PRahaarshield_Miniproject\models\` (replace v2):
`muril_multitask.pt`, `muril_multitask_tokenizer\`, `muril_multitask_config.json`, `conv_model.pt`, `conv_config.json`
```
cd ..\app
python check_model.py          (now also says: conversation model ConvEngine)
python -m eval.run_eval --data ..\training      (~5-10 min)  -> send eval\eval_report.md to Claude
run_app.bat
```

## What is new in v3 (for testing)
| Feature | Where you see it |
|---|---|
| Setup wizard (language, account type, name, group, contacts, safe/blocked, number) | Start of the session; ⚙ icon |
| Editable chat name | ✏ next to the name |
| Explanations in English / हिंदी / मराठी | Setup or the EN/HI/MR tag |
| Risky words highlighted | Yellow marks in the message + "Risky words" in "why?" |
| Link / UPI / phone checks + Simulated I4C registry | Red flags + "Good to know" facts |
| Context (account type, contacts, foreign number, business name mismatch) | Banner, flags, facts |
| Conversation stage + M7 | Debug line under the banner (after v3 training: M7; before: rules) |
| Phone + laptop split | `/sim?view=user` on phone, `/sim?view=scam` on laptop (same Wi-Fi) |
