"""Shared constants for PrahaarShield (sprint version).

Every script imports labels from here so names never drift between
data prep, training, the engine and the brain.
"""

PILLARS = [
    "P_IDENTITY",   # claims to be someone trusted / official (bank, police, company, relative)
    "P_SITUATION",  # describes a (fake or real) problem/situation needing action
    "P_STAKES",     # threat of loss/punishment OR promise of a big reward
    "P_CRED",       # asks the READER to send a secret: OTP, PIN, password, CVV
    "P_RESOURCE",   # asks the READER to pay, install an app, open a link to enter details, or send documents/personal details
    "P_CONTROL",    # controls behaviour: keep secret, stay on call, don't contact anyone, act within minutes
]

SCAM_TYPES = [
    "digital_arrest",
    "kyc_bank",
    "courier_customs",
    "investment_group",
    "job_task",
    "lottery_prize",
    "loan_app",
    "utility_bill",
    "fake_relative",
    "sextortion_threat",
    "boss_impersonation",   # "this is your boss/CEO, urgently pay vendor / buy gift cards / open this file"
    "account_takeover",     # "send me the code I sent by mistake", WhatsApp renting / linked-device, fake WhatsApp support
    "malicious_file_link",  # wedding-invite APK, greeting links, "is this your photo?" bait
    "benign",
]

LANGUAGES = ["en", "hi_deva", "hinglish"]           # languages we generate + fully support
MODEL_LANGUAGES = LANGUAGES + ["other"]             # language head also learns "other" (Marathi, noise, emoji-only...)

# Which heads a row is allowed to train. 1 = use this label, 0 = masked (label missing/untrusted)
DEFAULT_MASK = {"is_scam": 1, "scam_type": 1, "pillars": 1, "language": 1}

STYLES = ["formal", "formal_typos", "slight_informal", "slight_informal_typos", "short_direct",
          "short_direct_typos", "casual", "casual_typos", "urgent_caps", "broken_english", "friendly", "short",
          "promotional", "promotional_typos"]

PLACEHOLDERS = ["<URL>", "<UPI_LINK>", "<UPI>", "<EMAIL>", "<PHONE>", "<PHONE_INTL>",
                "<AMOUNT>", "<ACCOUNT>", "<AADHAAR>", "<PAN>", "<CODE>"]

# Public helpline numbers that must NOT be turned into <CODE>/<PHONE> (they carry meaning)
HELPLINES = {"1930", "112", "100", "101", "102", "108", "1909", "155260", "14422"}

REQUIRED_FIELDS = ["id", "card_id", "group_id", "text", "is_scam", "scam_type",
                   "pillars", "language", "is_hard_negative", "style"]
