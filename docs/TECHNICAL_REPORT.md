# 07 — TEXT ENGINE v3 (Seva First edition)
### Message engine + Conversation engine + Identifier checks + Brain (text only)

This file **replaces `01_TEXT_MODULE.md` and `06_TEXT_ENGINE_COMPLETE_WORKFLOW.md` for the Seva First submission.**
Everything in 01/06 that still holds is carried over here; everything that changed is listed in Part 1 with the reason.
01/06 stay valid as the **long-term (ARM / on-phone) plan**.

**Submission:** Seva First Innovation Challenge, Maharashtra Zone · Sector 9 (Emerging Technologies) · Sub-theme 4: *Responsible AI, Deepfake Detection, Cyber Resilience and Digital Trust*
**Own target:** 25 Oct 2026 · **Official last date:** 30 Oct 2026 (buffer)

---

## PART 0 — STATUS AT A GLANCE

| Block | Status |
|---|---|
| Normalizer (fancy fonts, invisible chars, look-alike letters, spaced letters, defanged links, tricks recorded) | ✅ built |
| Entity extraction + placeholders (URL, UPI, PHONE, PHONE_INTL, AMOUNT, ACCOUNT, AADHAAR, CODE; helplines kept) | ✅ built |
| Dataset: 2,739 messages (815 scam / 1,924 benign), 4 languages, 6 scam types | ✅ built |
| M1 Message model (MuRIL multi-task: scam, type, 6 pillars, language) | ✅ trained · v3 retrain with testing fixes |
| M4 Binary baseline (same MuRIL, scam head only) | ✅ trained |
| Two-sided testing UI (user + scammer) with ✓/✗ feedback log | ✅ built |
| Brain v1 (levels L0–L4, stage timeline, SOS, EN/HI templates) | ✅ built · v2 below |
| **Session setup screens + context signals** | 🔨 build |
| **Identifier checks (phone / UPI / link) + simulated I4C Suspect Registry** | 🔨 build |
| **M7 Conversation model + conversation dataset** | 🔨 build |
| **Calibration, risky-word highlighting, 3-language explanations** | 🔨 build |
| **Evaluation pack (messages, chats, identifiers, tricks, real messages, per language)** | 🔨 build |
| Images, Llama explainer, phone student model, Android | ⏸ deferred (Part 16) |

---

## PART 1 — WHAT CHANGED vs 01 / 06 (and why)

| # | Item | 01 / 06 said | v3 (now) | Why |
|---|---|---|---|---|
| 1 | Scam types | 11 classes (incl. courier, lottery, sextortion, utility, fake relative) | **6 scam types + benign**: digital_arrest, kyc_bank, boss_impersonation, investment_group, job_task, loan_app | Your decision: depth over breadth for Seva; the trained model covers these 6 |
| 2 | Languages | English + Hindi only; Marathi = future / "other" | **English, Hinglish, Hindi (Devanagari), Marathi** are all *supported* | The dataset already contains 429 Marathi messages and the model scores Marathi well (test F1 1.00 on 38 messages) |
| 3 | Language gate (06 Step 2) | Marathi → `text_reliable = false` | Marathi → **reliable**; only "other" or < 3 real words → unreliable | Follows from #2; otherwise every Marathi message would be down-weighted |
| 4 | Language-ID model M6 | Separate tiny model | **MuRIL's own language head + a script check** (Devanagari vs Latin) | Saves building/training a model in 4 days; M6 returns in the phone phase |
| 5 | Max length | 128 tokens | **256 tokens** (long messages: overlapping chunks, riskiest kept) | Hinglish/Devanagari use more tokens; 128 cut real messages |
| 6 | Pooling | [CLS] vector | **Mean pooling** over all tokens | v1 with [CLS] + one learning rate collapsed the type head (F1 0.16); v2 fixed it (F1 0.97) |
| 7 | Head training | One learning rate | **Encoder 3e-5, heads 1e-3**; type head trained on scam rows only; pillar pos-weights; language + class weights | Same v1 → v2 lesson |
| 8 | Split | By scenario card, 85/15 | **By similarity group, 80/10/10, seed 2026** (`prepare_v3.py`): near-duplicate messages (char 3–5-gram cosine ≥ 0.60) form one group and stay in one split | The 7-field files have no card IDs; similarity groups give the same protection (no 'sibling' messages across train/test) without them |
| 9 | Data size | 5,000–8,000 | **2,739** messages (+ new conversation set) | Time; reported honestly |
| 10 | Teachers M2 IndicBERT v2, M3 XLM-R | Compare 3 | **MuRIL only** | Deferred to phone phase; MuRIL already beats the TF-IDF baseline by +9.5 F1 points |
| 11 | Student M5 + INT8 + ExecuTorch, parity test, phone benchmarks | Required | **Deferred** (laptop CPU inference now) | Seva judges idea, impact, feasibility; phone export is the ARM phase |
| 12 | Calibration (Step 7) | Temperature scaling | **Kept, now actually built** | Brain needs honest probabilities |
| 13 | Label cleaning | 5-fold teacher copies | **5-fold with the TF-IDF model** (seconds on the laptop) → top 100 disagreements → you decide keep / scam / benign / type / drop → applied on re-run | Same idea (independent out-of-fold opinion) without 5 GPU runs |
| 14 | Chat-level analysis | "Chat summary" from message scores (max, vote, pillar timeline) | Summary **kept** + **new learned Conversation model M7** | You asked for proper conversation-level detection |
| 15 | Number-risk list / Links module | "mock FRI" list, links sent to a separate module | **Identifier checker built inside the text engine** (phone, UPI, link) + **simulated I4C Suspect Registry** | Accuracy needs layers: your lists → registry → official lists → India rules → context |
| 16 | Context signals | Not in 01/06 (only "unsaved number", "forwarded") | **Session setup**: language, account type, chat name, single/group, contacts permission, safe/blocked/not-in-contacts, sender number | Simulates what WhatsApp/the phone already knows |
| 17 | Explanations | Templates EN + HI | **EN / HI / MR**, chosen by the user at the start of the session | Brain speaks the user's language |
| 18 | Evidence | Pillar templates | + **risky-word highlighting** (from the model's gradients) + identifier findings + context signals | Transparency is the core of "Responsible AI" |
| 19 | SOS guidance | Llama always woken | **Fixed, verified templates** (no free-text AI) | Llama deferred; templates are safer for advice like 1930 |
| 20 | Images / OCR in SOS | Included | **Deferred** (images shown as "not scanned yet") | Your decision: text only this round |
| 21 | Role head | Phase 2 | Phase 2 (unchanged) | — |
| 22 | Outgoing guard T6 | Phase 2 | Phase 2 (unchanged) | — |
| 23 | Training rule "no metadata" | No account age / sender data in training | **Unchanged and stricter:** context signals go **only into the Brain**, never into model training | v2 leak: metadata in training gave a fake AUC of 1.0 |

### Inconsistencies found while re-checking (now fixed in this file)
- 06 Step 2 marked Marathi unreliable while the data and UI support Marathi → fixed (#3).
- 06 Step 4 / Step 6 said 128 tokens and [CLS] → the trained model uses 256 and mean pooling (#5, #6).
- 01/06 listed 11 scam types; the trained model has 6 → fixed (#1).
- 01 split "by card" vs actual stratified split → stated honestly (#8).

---

## PART 2 — HACKATHON FIT (Seva First requirements → where we meet them)

| Requirement / judging focus | Where PrahaarShield meets it |
|---|---|
| Sector 9, sub-theme 4: Responsible AI, Cyber Resilience, Digital Trust | Whole system; Responsible-AI mapping in Part 13 |
| Problem: who is affected and how many | WhatsApp users facing digital-arrest, KYC, boss, investment, job and loan scams; national fraud-loss figures in the pitch |
| Solution + what is innovative | Conversation-level detection (stage: approach → pressure → demand), multilingual incl. Hinglish and Marathi, explanations in the user's language, government-registry-ready identifier checks |
| Feasibility & implementation | Working prototype (two-sided WhatsApp-style UI), trained models, measured results |
| Testing / validation evidence | Test results (Part 14) + your two-sided testing log + real-message test |
| Impact & scalability | Path to on-device feature inside WhatsApp; I4C / 1930 / NCRP / Chakshu integration |
| Government role | Evidence pack for 1930 / cybercrime.gov.in; integration-ready with I4C Suspect Registry; anonymised trend counts (opt-in) for cyber cells |
| Pitch deck: 6 slides | Title · Problem · Solution & innovation · Feasibility · Impact & scalability · Team & support required |
| Prototype / demo link (optional) | Demo video of the two-sided UI |

---

## PART 3 — ARCHITECTURE (text only)

```
SESSION SETUP (once per demo chat)                         TRIGGERS (from 06, unchanged)
language · account type · name · single/group ·            T1 Live guard · T2 Protect new chats
contacts permission · safe/blocked/not saved · number      T3 Check this chat · T4 Check all · T5 SOS
            │                                                        │
            ▼                                                        ▼
      CONTEXT SIGNALS ───────────────┐                     JOB (type, chat, messages, priority)
                                     │                               │
                                     │      ┌────────────────────────▼─────────────────────────┐
                                     │      │ TEXT ENGINE (per message, Steps 0–10, Part 6)    │
                                     │      │ normalize → language gate → entities → M1 MuRIL  │
                                     │      │ → calibration → highlights → evidence            │
                                     │      │        │ entities                                │
                                     │      │        ▼                                         │
                                     │      │ IDENTIFIER CHECKS (Part 7)                       │
                                     │      │ phone · UPI · link → simulated I4C registry,     │
                                     │      │ official lists, India rules                      │
                                     │      │        │ message vectors                         │
                                     │      │        ▼                                         │
                                     │      │ CONVERSATION ENGINE M7 (Part 9)                  │
                                     │      │ last 8 messages → chat scam prob + stage         │
                                     │      └────────────────────────┬─────────────────────────┘
                                     ▼                               ▼
                               ┌──────────────────────────────────────────┐
                               │ BRAIN v2 (Part 10)                       │
                               │ fusion → L0–L4 · hard rules · stage       │
                               │ timeline · alert policy · explanations    │
                               │ (EN/HI/MR) · SOS · evidence pack          │
                               └──────────────────────┬───────────────────┘
                                                      ▼
                           UI: tags · banner · STOP alert · SOS · "This is not a scam"
```

**Golden rule:** the **models read text only**. Context signals and identifier results join **only in the Brain**.

---

## PART 4 — SESSION SETUP & CONTEXT SIGNALS

### 4.1 The setup screens (testing UI and demo)

| Step | Screen text | Options |
|---|---|---|
| 1 | "Choose the language you prefer for this demo session" | English / हिंदी / मराठी |
| 2 | Account type | Business / Fraud / Scam / Regional scam / General |
| 3 | Chat name (editable) · Chat type | free text (e.g. Mahesh, Auntie, Bull Run VIP) · Single / Group |
| 4 | Allow access to saved contacts for better accuracy? | Yes / No |
| 5 | (only if Yes) This number is | Safe (saved contact) / Blocked / Not in contacts |
| 6 | Sender's phone number (editable) | e.g. +91 98XXXXXXXX, +92 …, 1600-XX-XXXX |

### 4.2 Meaning and Brain effect of each signal

| Signal | Meaning | Brain effect (Part 10.3) |
|---|---|---|
| General | Ordinary account, no history | Neutral |
| Business | WhatsApp business account | Neutral; **impersonation check**: message claims a different organisation than the business name → +1 level |
| Fraud | Account previously reported for fraud | +1 level when the text is at least L1 |
| Scam | Confirmed scam account | Banner "This account was reported as a scam" from the first message (min L2) |
| Regional scam | Linked to a regional scam cluster | +1 level when the text is at least L1 |
| Safe contact | Saved, trusted contact | −1 level, **never below a hard-rule floor**, never hides L3+ text (hacked friends) |
| Blocked | User blocked this number before | +1 level |
| Not in contacts | Unknown number | Neutral, "unknown number" shown as context |
| Contacts permission = No | No contact info | Contact signals skipped |
| Group | Group chat | Each sender judged separately; group-scam patterns (VIP trading, task groups) |

**Responsible-AI rule:** a context signal alone can **never** make a message L3+ or call a message a scam. With benign text, the user sees "This account was reported" (a fact), not "This message is a scam" (an accusation).

### 4.3 How this works on a real phone later (not in this round)

| Setup step | Real phone |
|---|---|
| Language | First-run app setting |
| Account type | Comes automatically from WhatsApp's servers (demo: picker labelled "simulated") |
| Contacts permission | Normal Android permission pop-up |
| Safe / Blocked / Not saved | Read automatically from contacts + WhatsApp block list |
| Name, single/group, number | From the chat itself |

**Final demo layout:** phone = user view (`/sim?view=user`); laptop = scammer view + demo control panel with the setup answers (`/sim?view=scam`).

---

## PART 5 — TRIGGERS & JOBS (from 06 Part A, unchanged)

| # | Trigger | Checks | This round |
|---|---|---|---|
| T1 | Live guard | Each new incoming message | ✅ |
| T2 | Protect new chats & groups | First messages from unsaved numbers / new groups | ✅ |
| T3 | Check this chat | Whole chat, oldest → newest | ✅ |
| T4 | Check all chats | Chat by chat, pause/resume | ✅ simple |
| T5 | 🆘 SOS | Whole chat, deep report | ✅ (text only, templates) |
| T6 | Outgoing guard | What the user is about to send | ⏸ Phase 2 |

Job priority: SOS 1 > LIVE 2 > CHECK_CHAT 3 > NEW_CHAT 4 > CHECK_ALL 5 (SOS pauses CHECK_ALL).

---

## PART 6 — PER-MESSAGE PIPELINE (Steps 0–10, updated)

| Step | What | v3 details |
|---|---|---|
| 0 Skip / cache | Skip outgoing, system, empty, emoji-only; reuse result if the cleaned-text fingerprint was seen | Outgoing (user's own) messages are never scored; "added to group by unknown number" passed to Brain as an event |
| 1 Normalizer | 1a NFKC · 1b invisible chars · 1c look-alike letters (Devanagari untouched) · 1d spaced letters · 1e defanged links · 1f tricks recorded | ✅ built; `obfuscation_detected` is evidence |
| 2 Language gate | en / hinglish / hi_deva / mr / other | MuRIL language head + script check; **reliable** if supported language and ≥ 3 real words |
| 3 Entities + placeholders | URL, UPI, PHONE, PHONE_INTL, AMOUNT, ACCOUNT (masked), AADHAAR (masked), CODE; helplines (1930 etc.) kept | ✅ built; entities also sent to **Identifier checks** (Part 7); same function in training and inference |
| 4 Chunking | > 256 tokens → overlapping chunks | Score = riskiest chunk |
| 5 Tokenizer | MuRIL WordPiece | — |
| 6 M1 Message model | One pass → scam prob, scam type (6), 6 pillars, language, **768-d message vector** | Vector feeds M7 |
| 7 Calibration + gate | Temperature scaling per head (learned on validation) · decision threshold tuned on validation (≤ 5% false alarms) · pillar thresholds | Unreliable text → `reliable:false`, never shown as "Safe ✅" |
| 8 Evidence builder | Pillar templates (EN/HI/MR) · rule hits · **risky-word highlights** | Highlights = top words by gradient × input on the scam head, merged to whole words, only if score ≥ L2 |
| 9 Save result | Session memory (laptop); phone: encrypted local DB, 7-day retention | No second copy of message text on the phone |
| 10 Send to Brain | LIVE/NEW_CHAT: per message · T3/T4/T5: + chat summary + M7 output | — |

**Hard rules (computed in Step 8, enforced in the Brain):**

| Rule | Example | Floor |
|---|---|---|
| `cred_ask` | "OTP bata do", "share the PIN" | L3 |
| `screen_share_app` | AnyDesk, TeamViewer, QuickSupport, `.apk` install | L3 |
| `upi_pin_collect` | "enter PIN to receive money", "approve collect request" | L3 |
| `gift_codes` | "send gift card codes" | L3 |
| `safe_account` | "transfer to RBI safe account / verification account" | L3 |

### Output of the text engine for one message
```json
{
  "msg_id": "sim-4", "language": "hinglish", "reliable": true,
  "scam_score": 0.93, "scam_type": {"top": "digital_arrest", "p": 0.88},
  "pillars": {"P_IDENTITY":0.94,"P_SITUATION":0.71,"P_STAKES":0.90,"P_CRED":0.05,"P_RESOURCE":0.12,"P_CONTROL":0.87},
  "rules": ["safe_account"], "obfuscation_detected": false,
  "highlights": ["Mumbai police", "arrest", "kisi ko mat batana"],
  "entities": {"PHONE_INTL": 1, "AMOUNT": 1},
  "identifiers": [{"type":"phone","value":"+92 3xx…","findings":["international number (Pakistan)"],"risk":"note"}],
  "evidence": [
    {"id":"T1","kind":"P_IDENTITY","en":"Claims to be police / officials","hi":"खुद को पुलिस / अधिकारी बता रहा है","mr":"स्वतःला पोलीस / अधिकारी असल्याचे सांगतो"},
    {"id":"T2","kind":"P_CONTROL","en":"Tells you to keep it secret or stay on a call","hi":"छुपाने या कॉल पर रहने को कह रहा है","mr":"गुप्त ठेवायला किंवा कॉलवर राहायला सांगतो"}
  ],
  "vector_ref": "emb_sim-4"
}
```

---

## PART 7 — IDENTIFIER CHECKS (phone · UPI · link)

Each identifier found in Step 3 (and the sender number from setup) goes through **five layers, most certain first**. Every layer adds findings; the Brain combines them.

| Layer | Phone number | UPI ID | Link |
|---|---|---|---|
| 1 User's own lists | Safe / Blocked / Not in contacts | — | — |
| 2 Simulated I4C Suspect Registry (Part 8) | Exact match → report count, scam type, last seen | Exact match | Exact domain match |
| 3 Official lists | Official series: **1600ABCXXX government, 1601ABCXXX financial institutions** (TRAI); **140** = registered telemarketing; 1800 toll-free; national helplines (1930, 112…) | Known bank/PSP handles (`@oksbi`, `@okhdfcbank`, `@okicici`, `@okaxis`, `@ybl`, `@ibl`, `@axl`, `@paytm`, `@upi` …) | Official domains: `.gov.in`, `.nic.in`, bank and regulator sites (sbi.co.in, onlinesbi.sbi, hdfcbank.com, icicibank.com, rbi.org.in, sebi.gov.in, incometax.gov.in …) |
| 4 India-specific rules | +91 then 10 digits starting 6–9; wrong length → invalid; **foreign country code → named in the explanation only (never blocked)**; "bank / KYC team" from an ordinary mobile → caution note (banks use 1600/1601 for service calls) | Format `name@handle`; unknown handle → caution; personal-looking UPI for a "government fine / RBI / police" payment; payee name ≠ claimed organisation; "receive money by entering PIN" | Look-alike spelling of a brand (edit distance ≤ 2: `sbi-kyc`, `hdfcbnak`); brand in subdomain/path of another domain; punycode / mixed scripts; URL shorteners; raw IP; `http` for a login page; `.apk` / `.exe`; unusual endings (`.xyz`, `.top`, `.online`, `.site`) |
| 5 Context | Combined with message scam score + conversation stage | same | same |

**Caution, not proof:** the 1600 series is official but can be misused; an ordinary mobile number is not proof of fraud. Such findings appear as *notes* in the explanation, they do not raise the level alone.

**Risk output per identifier:** `registry_hit` (strong) · `suspicious` (rule hits) · `note` (fact only, e.g. foreign number) · `official` (matches an official list) · `unknown`.

**Accuracy test:** a list of ~150 identifiers (genuine + fake, all kinds) with expected results → precision / recall reported in the results.

**Online checks** (Google Safe Browsing, domain age / WHOIS) need internet → "future: online mode". The demo stays offline for privacy.

---

## PART 8 — SIMULATED I4C SUSPECT REGISTRY

**Real-world basis:** I4C (Ministry of Home Affairs) launched the Central Suspect Registry on 10 Sep 2024 with banks and financial institutions: a central database of cybercrime suspect identifiers (phone numbers, account details, device data) shared with participating entities.

**What we build:** `registry/suspect_registry_SIMULATED.json`, **clearly labelled simulated demo data** in the file, the UI ("Simulated I4C Suspect Registry (demo data)") and the pitch.
Pitch line: *"Integration-ready with I4C's Suspect Registry; the demo uses simulated data; real deployment would connect through a government partnership."*

| Field | Example |
|---|---|
| `identifier_type` | phone / upi / bank_account / url_domain |
| `value` | `+91 70XXX 45210`, `refund.help@ybl`, `sbi-yono-kyc-update.in` |
| `scam_type` | one of our 6 types |
| `report_count` | 14 |
| `first_reported`, `last_reported` | 2026-08-02, 2026-10-19 |
| `state` | spread across India (not Maharashtra only) |
| `risk_level` | medium / high / very_high |
| `status` | active / under_investigation |

Size: ~300 entries (≈ 50 per scam type) + the identifiers used in the demo scripts, so the live demo shows real hits.

---

## PART 9 — CONVERSATION ENGINE (M7, new)

### 9.1 What it answers
"Looking at the chat **so far**, is this a scam conversation, what type, and **which stage** has it reached?" Stages: `none` → `approach` (who they claim to be, the situation) → `pressure` (threat, reward, secrecy, urgency) → `demand` (money, OTP, app, documents).

### 9.2 Model
```
each message ──► M1 (frozen) ──► 768-d vector  + speaker tag (them / me) + position
last 8 messages ──► small transformer (2 layers, 4 heads, ~3M parameters)
                ──► head A: chat is_scam   head B: current stage (4)   head C: scam type (6)
```
- Reuses M1's work (no second big model); trains in minutes on Colab; small enough for phones later.
- Runs after every incoming message (LIVE) and over the full chat (T3/T4/T5).

### 9.3 Conversation dataset (we build it; nothing public fits Indian WhatsApp chats in our languages)

| Source | What | Target size | Used for |
|---|---|---|---|
| A. Written full chats | Multi-turn scam chats in real script order with user replies ("kaun?", "kya hua?", "ok") in EN / Hinglish / HI / MR; per-message stage labels | ~240 (40 per type) + ~40 slow-burn (friendly first, scam later) | Train / validation |
| B. Assembled chats | Scam messages from our dataset ordered by stage (pillars → stage) + typical replies | ~600 | Train (volume) |
| C. Benign chats | Written (family money, bank-alert threads, office urgency, a friend warning about scams, group notices) + assembled from casual + hard-negative messages | ~250 written + ~600 assembled | Train / validation |
| D. Your UI chats | Logged from the two-sided UI | as many as you test | **Test only** |

Labels per chat: `is_scam`, `scam_type`, `stage` of every message, index of the **turning point** (first scam message). Split by chat source / script (no chat in two splits).

**Honest limitation:** sources A–C are written or assembled, not real chats; source D measures the real behaviour.

### 9.4 What happens to the old datasets (nothing is discarded)
1. They train **M1**, which is still needed: instant per-message warnings, pillars, highlights, and the vectors M7 reads.
2. Their messages are the **building blocks** of source B.
3. Hard negatives become **benign chats** (source C).
4. They remain the **single-message test**.

---

## PART 10 — BRAIN v2 (text only)

### 10.1 Inputs
M1 per message (calibrated) · M7 per chat · identifier findings · hard rules · context signals (Part 4) · events (added to group by unknown number) · user feedback ("not a scam").

### 10.2 Severity levels
| Level | Name | Meaning | UI |
|---|---|---|---|
| L0 | Safe | No scam signs | nothing (✓ checked after a scan) |
| L1 | Caution | Weak signs | no alert; visible only in SOS / details |
| L2 | Suspicious | Clear scam signs | yellow tag + banner |
| L3 | Dangerous | Strong signs or a hard rule | orange tag + banner + notification |
| L4 | Critical | Scam has reached the **demand** stage | full-screen STOP alert |

### 10.3 Fusion (transparent rules, no black box)
1. **Text level** from max(M1 message score, M7 chat score): < 0.30 → L0 · < threshold → L1 · < 0.80 → L2 · ≥ 0.80 → L3.
2. **Hard-rule floor:** any Part 6 hard rule → at least L3.
3. **Identifier adjustment:** registry hit → +1 (at least L2) · rule-based `suspicious` → +1 if text ≥ L1 · `note` / `official` → explanation only.
4. **Context adjustment** (Part 4.2), at most ±1 level, never below a hard-rule floor, never creating L3+ from context alone.
5. **L4:** level ≥ L3 **and** stage = demand (M7, or the stage timeline reached demand after approach/pressure in the last 6 incoming messages).
6. **Unreliable text** (other language / too short): text level capped at L1 unless a hard rule or registry hit applies; UI says "not fully checked", never "Safe".

### 10.4 Alert policy
- Alert only when the level **rises** (one alert per stage, no spam).
- After "This is not a scam": quiet until **new strong evidence** (L3+ or a hard rule).
- Groups: per-sender memory; banner names the sender.

### 10.5 Explanations (English / हिंदी / मराठी, from the setup choice)
Fixed, verified templates (no free-text AI): what is happening (per scam type) · red flags (pillars, rules, highlights, identifier findings, context facts) · where you are in the scam (stage timeline) · what usually comes next · what to do now.

Examples (EN): "This number appears 14 times in the Simulated I4C Suspect Registry for digital-arrest fraud." · "This is an international number (+92)." · "Banks contact customers from official 1600/1601 numbers; this is an ordinary mobile number."

### 10.6 SOS report + evidence pack
Verdict · stage timeline with the exact messages · next likely step · red flags · actions: **Call 1930**, **cybercrime.gov.in**, **Sanchar Saathi (Chakshu)**, block & report · **evidence pack** (flagged messages, identifiers, times), created only when the user asks.

### 10.7 Human control
Never auto-blocks or deletes · "This is not a scam" always available · user can turn live guard off · every alert explains itself.

---

## PART 11 — MODELS FOR THIS ROUND

| # | Model | Status | Runs where |
|---|---|---|---|
| M1 | MuRIL multi-task message model | ✅ v2 trained → **v3 retrain** (testing fixes + calibration) | Laptop CPU |
| M4 | MuRIL binary baseline | ✅ trained (comparison only) | — |
| M7 | Conversation model (small transformer over M1 vectors) | 🔨 new | Laptop CPU |
| Helpers | TF-IDF baseline, cheater model (leakage check) | ✅ | Laptop |
| Deferred | M2 IndicBERT v2, M3 XLM-R, M5 student + INT8 + ExecuTorch, M6 language-ID | ⏸ phone phase | — |

**Models used but not trained:** Claude (writing data in conversation); no external AI at run time.

---

## PART 12 — DATASETS FOR THIS ROUND

| # | Dataset | Status | Used for |
|---|---|---|---|
| D2 | Message dataset: `scam_dataset` 815 + `benign_dataset` 1,071 + `hard_negatives_dataset` 853 = 2,739 | ✅ | M1 train / val / test |
| D2-v3 | Fixes from your ✗ testing log (relabels + new rows where the model failed) | 🔨 | M1 v3 |
| C1 | Conversation dataset (Part 9.3, sources A–C) | 🔨 | M7 train / val |
| C2 | Your UI chats (source D) | 🔨 ongoing | M7 + Brain **test only** |
| R1 | Simulated I4C Suspect Registry (~300 entries) | 🔨 | Identifier checks |
| R2 | Official lists (bank / gov domains, PSP handles, number series, helplines) | 🔨 | Identifier checks |
| T1 | Identifier test list (~150) | 🔨 | Checker precision / recall |
| D5 | Real scam messages (you collect, anonymised) | 🔨 | **Test only** |
| D4 | Real benign messages | 🔨 if time | **Test only** |
| D6 | Trick (adversarial) test set: look-alike letters, zero-width, spacing, Roman ↔ Devanagari swaps, emoji spam, typos | 🔨 script | Robustness test |
| F1 | Feedback log (✓/✗ from the UI) | ✅ running | Error analysis → D2-v3 |

---

## PART 13 — RESPONSIBLE-AI MAPPING (Sector 9 · sub-theme 4)

| Principle | How it is built in |
|---|---|
| Privacy | All analysis local (laptop now, phone later); no message leaves the device; evidence pack only on user request; account/Aadhaar numbers masked inside the engine |
| Transparency | Highlighted words, scam type, pillars, identifier facts, stage timeline, in the user's language |
| Human control | No auto-block / delete; "This is not a scam"; live guard can be switched off |
| Fairness | Results per language (EN / Hinglish / HI / MR); language-balanced training weights |
| No accusation by label | Context signals can't create L3+ alone; wording "looks like a scam", facts stated as facts |
| Robustness | Normalizer + trick test set |
| Honest confidence | Calibration; "not fully checked" for unsupported text |
| Accountability | Model card, data card, limitations (Part 15), simulated data clearly labelled |
| Government integration | 1930 / NCRP / Chakshu actions; I4C Suspect Registry-ready; opt-in anonymised trend counts for cyber cells |

---

## PART 14 — EVALUATION PLAN

### 14.1 Current results (test set, 273 messages: 81 scam / 192 benign)

| Model | Macro-F1 | Scam F1 | Scam recall | False alarms | Scam-type F1 | Pillar micro-F1 |
|---|---|---|---|---|---|---|
| TF-IDF + LR | 0.891 | 0.847 | 85.2% | 6.8% | 0.851 | – |
| MuRIL binary (M4) | 0.957 | 0.940 | 96.3% | 3.6% | – | – |
| **MuRIL multi-task (M1)** | **0.958** | **0.942** | **100%** | 5.2% | **0.966** | 0.764 (P_CRED 0.25) |

Per-language macro-F1 (M1): English 0.963 · Hinglish 0.937 · Hindi 0.933 · Marathi 1.000.

### 14.2 v3 evaluation suite and targets (targets to measure, not promises)

| Test | Metric | Target |
|---|---|---|
| Message test split | Scam recall / false alarms | ≥ 97% / ≤ 5% |
| Per language | Macro-F1 gap between languages | ≤ 0.05 |
| Calibration | ECE | < 0.05 |
| Conversation test (written + your UI chats) | Scam chats reaching L4 at the demand stage | ≥ 90% |
| Benign chats | Chats wrongly alerted (L3+) | ≤ 5% |
| Slow-burn chats | No alert before the turning point | ≥ 90% |
| Identifier list | Precision of `suspicious` + `registry_hit` | ≥ 0.95 |
| Trick test set | Scam recall drop vs clean text | ≤ 5 points |
| Real scam messages | Recall (sample size reported) | report honestly |
| Speed (laptop CPU) | ms per message, ms per chat check | report |

---

## PART 15 — KNOWN LIMITATIONS (stated openly)
- Most training text is written from reported cases, not collected real chats; conversations are written or assembled.
- Small test sets (81 test scams): "100% recall" realistically means about 95–100%.
- P_CRED is weak in the model (few examples); covered by the `cred_ask` hard rule.
- 6 scam types only; other scams may be missed or misnamed.
- Registry is simulated; account types are simulated by the setup screen.
- Laptop inference; on-phone version not yet built.
- Text only: images, voice notes and link contents are not analysed.

---

## PART 16 — DEFERRED (next steps slide)
Images (OCR, QR, image classifier) · Llama explainer · M2/M3 teacher comparison · M5 student + INT8 + ExecuTorch on the S25 FE · M6 language-ID · role head · outgoing guard (T6) · more scam types · online link checks · real I4C / DoT integration · Android app.

---

## PART 17 — CODE LAYOUT

```
app/
├── engine/
│   ├── normalizer.py          ✅ Step 1
│   ├── entities.py            ✅ Step 3
│   ├── text_engine.py         ✅ M1 loader + Steps 2,4–8   → add calibration, highlights
│   ├── identifiers.py         🔨 Part 7 (phone / UPI / link checks)
│   └── conversation.py        🔨 M7 loader + chat inference
├── brain/
│   ├── brain.py               ✅ v1 → 🔨 v2 fusion, context, alert policy
│   └── templates_{en,hi,mr}.json   🔨 explanations
├── registry/
│   ├── suspect_registry_SIMULATED.json   🔨
│   └── official_lists.json               🔨
├── server/main.py             ✅ API  → add setup/session endpoints
├── frontend/sim.html          ✅ your UI → add setup screens, user/scam views
├── eval/                      🔨 run_eval.py, tricks.py, identifier_tests.json
└── feedback/                  ✅ ✗ log
training/
├── train_muril_v3.ipynb       🔨 M1 v3 + calibration
└── train_conversation.ipynb   🔨 M7
data/
└── conversations/             🔨 written + assembled chats
```

---

## PART 18 — TIMELINE (build done 22 Oct; buffer to 30 Oct)

| When | Who | What |
|---|---|---|
| 22 Oct ✅ | Claude | All code: identifier checks, simulated registry, Brain v2 (3 languages), engine v3 (calibration, highlights, features), M7 code, prepare_v3, conversation dataset, train_v3.ipynb, setup UI, evaluation suite |
| 22 Oct | You | Test v2 model in the new UI → ✗ CSV · review_queue.csv (~30 min) · run prepare_v3 + build_conversations · Colab train_v3 (~1 h) |
| 23 Oct | You + Claude | Copy models_v3 → laptop · check_model.py · run_eval.py → send report · fixes |
| 24 Oct | You + Claude | 6-slide pitch · model card · demo video |
| 25 Oct | You | Register, Aadhaar, upload |

## PART 19 — REFERENCES
- S. Khanuja et al., "MuRIL: Multilingual Representations for Indian Languages," arXiv:2103.10730, 2021.
- J. Devlin et al., "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding," NAACL 2019.
- C. Guo et al., "On Calibration of Modern Neural Networks," ICML 2017 (temperature scaling).
- C. Northcutt et al., "Confident Learning: Estimating Uncertainty in Dataset Labels," JAIR 2021.
- P. Belém et al., "Weakly Supervised Multi-task Learning for Concept-based Explainability," ICLR 2021 workshop.
- M. Sundararajan et al., "Axiomatic Attribution for Deep Networks," ICML 2017 (gradient-based attributions).
- Unicode Technical Standard #39, "Unicode Security Mechanisms" (confusables).
- I4C / Ministry of Home Affairs: Central Suspect Registry, launched 10 Sep 2024 (newsonair.gov.in, cyberpeace.org).
- TRAI: 1600-series (1600ABCXXX government, 1601ABCXXX financial institutions) for service/transactional calls; 140-series for promotional calls (trai.gov.in press release 30/2024; news reports 2026).
- Seva First Innovation Challenge, Maharashtra Zone: sevainnovationchallenge.in (guidelines, FAQ).
