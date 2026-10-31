# PrahaarShield App – Setup & Demo Guide

## Folder layout (on your laptop)
```
C:\PRahaarshield_Miniproject\
   models\                     <- you already have these 3
      muril_multitask.pt
      muril_multitask_tokenizer\
      muril_multitask_config.json
   app\                        <- unzip this package's "app" folder here
      engine\  brain\  server\  frontend\  demo\  common\
      check_model.py  run_app.bat  requirements.txt
```

## 1. Install (once, ~10 min)
Open the VS Code terminal in `C:\PRahaarshield_Miniproject\app`:
```
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

## 2. Check the model (1 min)
```
python check_model.py
```
You should see 5 lines: the 3 scam messages High (Dangerous/Suspicious), the 2 normal ones Safe, ~100-300 ms each.
If you see an error, paste it to Claude.

## 3. Start the app
Double-click `run_app.bat` (or run `python -m uvicorn server.main:app --host 0.0.0.0 --port 8000`).
- Windows Firewall pops up → tick **Private networks** → Allow.
- Laptop: open http://localhost:8000
- Phone (same Wi-Fi): run `ipconfig` on the laptop, note **IPv4 Address** (e.g. 192.168.1.7), open `http://192.168.1.7:8000` on the phone.
- Scammer panel (laptop browser): http://localhost:8000/sender

## 4. Demo flow (5 minutes)
1. **Phone**: chat list with 10 chats (family, college, society, friend + scams). Nothing checked yet.
2. **⋮ → PrahaarShield: Check all chats** → summary (checked / flagged / critical); shields appear on scam chats only.
3. Open **+91 70XXX 45210** → red banner, ⚠ markers on messages → tap a marker → why it is risky (EN/हिं).
4. Press **🆘 SOS** → verdict, scam stage timeline (approach → pressure → demand), red flags, what to do now,
   Call 1930 / cybercrime.gov.in / Chakshu / Evidence pack.
5. **Live attack**: on the laptop scammer panel press **Play** on "Digital arrest (live)". On the phone a new
   unknown chat appears; the alert escalates as messages arrive and turns into the full-screen **STOP** alert.
6. Play "WhatsApp code (account takeover)" → flagged instantly (OTP request rule).
7. Play "Normal friend" → no alert (no false alarm).
8. ⋮ → Language: हिंदी → explanations switch to Hindi.
9. Open Mummy / Society / College chats → safe, even though they mention fees, OTP warnings and deadlines.
10. ⋮ → Reset demo to start again.

## Troubleshooting
| Problem | Fix |
|---|---|
| Phone can't open the page | Same Wi-Fi? Firewall allowed for Private network? Use the IPv4 of the Wi-Fi adapter. Some college Wi-Fi blocks device-to-device: use your phone hotspot for the laptop instead. |
| `ModuleNotFoundError: engine` | Run commands from inside the `app` folder. |
| Model load error | Check the 3 files are in `..\models\`. Paste the error to Claude. |
| Slow first message | First prediction warms up the model (2-3 s); later ones ~0.1-0.3 s. |

## How it works (for the report)
`text -> normalizer (undo look-alike letters, invisible chars) -> placeholders (<URL>, <PHONE>, <AMOUNT>...)
-> fine-tuned MuRIL multi-task (scam prob, scam type, 6 intent pillars, language) -> rules (OTP/PIN ask, APK,
UPI collect, gift codes) -> Brain: severity L0-L4 per message, chat memory escalation to L4 when the scam
reaches the demand stage, SOS report with stage timeline, EN/HI explanations, verified action steps.`
All AI runs locally on the laptop; nothing is sent to any cloud service.
