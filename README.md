# PrahaarShield 🛡️
**The scam guard that reads the whole WhatsApp chat — and warns you before you pay.**
English · हिंदी · मराठी · Hinglish  ·  on-device  ·  Seva First Innovation Challenge 2026 (Sector 9: Responsible AI & Digital Trust)

Scams rarely arrive in one message. A "police officer" builds trust, then pressure, then demands money — in the victim's own language,
and each message alone looks harmless. PrahaarShield follows the conversation, explains *why* it is dangerous, and guides the user to 1930.

## What it does
| Step | What happens |
|---|---|
| **Clean** | Undoes tricks: look-alike letters, hidden characters, s p a c e d words, defanged links |
| **Read** | Fine-tuned **MuRIL** (Google) multi-task model: scam or not · 6 scam types · manipulation pillars · language |
| **Check** | Links, UPI IDs and phone numbers vs official lists (TRAI series, .gov.in, bank handles) and a scam registry *(simulated in this demo)* |
| **Reason** | Whole-chat **Brain**: money requests and escalation, threats, blocked calls, relationships (family OTP vs bank/WhatsApp code), victim actions, 19 local fact checks (RBI, I4C, SEBI, MSEDCL, NPCI, police advisories) |
| **Act** | 5 alert levels, full-screen STOP at the critical moment, SOS report with reasons in EN/HI/MR, 1930 + cybercrime.gov.in, evidence pack |

Scam types (financial only): digital arrest · KYC / bank · boss & known-contact impersonation · investment groups · job / task · loan apps.

## Results (honest)
Held-out test set, 434 messages, used once:
- **94.4%** of scams caught (95% range 90.6–97.6%) · **3.3%** false alarms · macro-F1 **0.956**
- per language (macro-F1): English 0.93 · Hindi 0.98 · Hinglish 0.98 · Marathi 0.95
- 20 hand-written test chats: 14/14 scam chats flagged, 0/6 normal chats alerted

**Limits:** all test data is synthetic or LLM-written · not yet field-tested · the scam registry is simulated ·
an AI assistant (Claude) helped write code and synthetic training messages; model choices were made by controlled experiments (several seeds, held-out test).

**What we learned:** a model trained only on our own messages scored 0.75 on another writer's texts; adding the independent
[Ridham115 audited dataset](https://huggingface.co/datasets/Ridham115/indian-scam-sms-synthetic-audited) (CC BY 4.0) raised that to 0.93.
A learned conversation model lost to transparent rules, so the app ships the rules.

## Run it
```bash
pip install -r app/requirements.txt
# download the model folder (≈1 GB) from: <https://drive.google.com/drive/folders/1ZBiNA9QSeHSXyP8l6L8PzRzrP2jrnwER?usp=sharing>
# Windows PowerShell:
$env:PRAHAAR_MODEL_DIR="C:\path\to\models_final"
cd app
python selftest.py          # quick check: threshold 0.86
.\run_app.bat               # then open http://localhost:8000/sim
```
`/sim` is a two-sided WhatsApp-style simulator (scammer on one side, user on the other). Press **SOS** to see every message explained.

## Repository
```
app/        FastAPI server, engine (normalizer, entities, MuRIL text engine, identifier checks), Brain (reasoning, fact library), frontend
training/   data preparation, style augmentation, outside-data fetcher, training notebooks (Colab), our datasets
```
Retrain: `cd training` → `python fetch_external.py` → `python make_style_aug.py` → `python prepare_v3.py` → run the notebook on Colab (T4).

## Credits
MuRIL (Google) · Ridham115 Indian scam SMS dataset (CC BY 4.0) · public advisories from I4C, RBI, SEBI, Mumbai Police, MSEDCL.
Built by **Anushka Bhakare**, TY B.Tech Computer Engineering, Cummins College of Engineering for Women, Pune.
