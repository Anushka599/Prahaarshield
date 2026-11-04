# PrahaarShield ðŸ›¡ï¸
**The scam guard that reads the whole WhatsApp chat â€” and warns you before you pay.**
English Â· à¤¹à¤¿à¤‚à¤¦à¥€ Â· à¤®à¤°à¤¾à¤ à¥€ Â· Hinglish  Â·  on-device  Â·  Seva First Innovation Challenge 2026 (Sector 9: Responsible AI & Digital Trust)

Scams rarely arrive in one message. A "police officer" builds trust, then pressure, then demands money â€” in the victim's own language,
and each message alone looks harmless. PrahaarShield follows the conversation, explains *why* it is dangerous, and guides the user to 1930.

## What it does
| Step | What happens |
|---|---|
| **Clean** | Undoes tricks: look-alike letters, hidden characters, s p a c e d words, defanged links |
| **Read** | Fine-tuned **MuRIL** (Google) multi-task model: scam or not Â· 6 scam types Â· manipulation pillars Â· language |
| **Check** | Links, UPI IDs and phone numbers vs official lists (TRAI series, .gov.in, bank handles) and a scam registry *(simulated in this demo)* |
| **Reason** | Whole-chat **Brain**: money requests and escalation, threats, blocked calls, relationships (family OTP vs bank/WhatsApp code), victim actions, 19 local fact checks (RBI, I4C, SEBI, MSEDCL, NPCI, police advisories) |
| **Act** | 5 alert levels, full-screen STOP at the critical moment, SOS report with reasons in EN/HI/MR, 1930 + cybercrime.gov.in, evidence pack |

Scam types (financial only): digital arrest Â· KYC / bank Â· boss & known-contact impersonation Â· investment groups Â· job / task Â· loan apps.

## Results (honest)
Held-out test set, 434 messages, used once:
- **94.4%** of scams caught (95% range 90.6â€“97.6%) Â· **3.3%** false alarms Â· macro-F1 **0.956**
- per language (macro-F1): English 0.93 Â· Hindi 0.98 Â· Hinglish 0.98 Â· Marathi 0.95
- 20 hand-written test chats: 14/14 scam chats flagged, 0/6 normal chats alerted

**Limits:** all test data is synthetic or LLM-written Â· not yet field-tested Â· the scam registry is simulated Â·
an AI assistant (Claude) helped write code and synthetic training messages; model choices were made by controlled experiments (several seeds, held-out test).

**What we learned:** a model trained only on our own messages scored 0.75 on another writer's texts; adding the independent
[Ridham115 audited dataset](https://huggingface.co/datasets/Ridham115/indian-scam-sms-synthetic-audited) (CC BY 4.0) raised that to 0.93.
A learned conversation model lost to transparent rules, so the app ships the rules.

## Run it
```bash
pip install -r app/requirements.txt
# download the model folder (â‰ˆ1 GB) from: <https://drive.google.com/drive/folders/1ZBiNA9QSeHSXyP8l6L8PzRzrP2jrnwER?usp=sharing>
# Windows PowerShell:
$env:PRAHAAR_MODEL_DIR="C:\path\to\models_final"
cd app
python selftest.py          # quick check: threshold 0.86
.\run_app.bat               # then open http://localhost:8000/sim
```
`/sim` is a two-sided WhatsApp-style simulator (scammer on one side, user on the other). Press **SOS** to see every message explained.

## Repository
```
app/          the working product: engine (model + checks), brain (reasoning), server, frontend demo, eval
training/     datasets and data-preparation scripts; notebooks/ holds the Colab training notebooks
docs/         technical report, run guide, testing guide, pitch deck
```
Retrain: `cd training` â†’ `python fetch_external.py` â†’ `python make_style_aug.py` â†’ `python prepare_v3.py` â†’ run the notebook on Colab (T4).

## Credits
MuRIL (Google) Â· Ridham115 Indian scam SMS dataset (CC BY 4.0) Â· public advisories from I4C, RBI, SEBI, Mumbai Police, MSEDCL.
Built by **Anushka Bhakare**, TY B.Tech Computer Engineering, Cummins College of Engineering for Women, Pune.
