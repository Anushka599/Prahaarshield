# PrahaarShield – Two-sided testing (your UI)

## Start
1. Put the `app` folder next to `models` (C:\PRahaarshield_Miniproject\app). The app also finds C:\PRahaarshield_Miniproject\models on its own.
2. `python check_model.py` → 5 lines (scam lines high, normal lines Safe). Paste errors to Claude.
3. Double-click `run_app.bat` → open **http://localhost:8000/sim**

## Screen
- **Left = Shyna (user)**. Incoming messages get ⚠ tags, the banner shows chat danger, SOS gives the full report.
- **Right = Unknown Person (you as the scammer)**. Only the right side's messages are checked; Shyna's own messages are never scored.
- Right header tools: 🐞 scores on/off · EN/HI explanations · ⟲ clear chat · ⬇ download wrong-prediction CSV · counter.

## Under every checked message (🐞 on)
`L3 · p=0.94 · digital_arrest (91%) · hinglish` / pillars / rules → **✓ right** or **✗ wrong** (+ optional note).
Every ✗ is saved to `app/feedback/feedback_log.jsonl` with the last 3 messages as context. Send the CSV to Claude daily.

## Test plan (aim for 150+ messages total)
| Round | What to type as the scammer | Expect |
|---|---|---|
| 1 Each scam type | 5–8 message conversations: digital arrest, KYC, boss, investment, job, loan | Rises to Dangerous, then Critical at the money/OTP demand |
| 2 Languages | Same scams in Hinglish, Hindi (Devanagari), Marathi | Same result in every language |
| 3 Benign look-alikes | Family asking money, bank OTP SMS, college fees, offers, a friend warning about scams | Stays Safe |
| 4 Tricks | Spaced letters (O T P), look-alike letters, emojis everywhere, short one-liners, typos | Still caught |
| 5 New scams | Types not trained (WhatsApp code takeover, sextortion, fake relative, electricity bill) | Note what happens, mark ✗ if missed |
| 6 Slow burn | 3–4 friendly messages first, scam starts later | Escalates only when it turns |
