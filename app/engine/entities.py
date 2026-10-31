"""Entity extraction + placeholders.

Finds observable FACTS (links, UPI IDs, phone numbers, amounts, ID-like numbers,
OTP-like codes) and replaces them with placeholders in the copy the model reads:

  "Pay ₹1,999 at sbi-kyc.in/verify or call +92 300 1234567"
  -> "Pay <AMOUNT> at <URL> or call <PHONE_INTL>"

Why: the text model should judge WORDING/INTENT; links go to the Links module,
numbers to the number-risk list. It also makes training data (fake numbers) and
real use look identical, and stops the model memorising random digits.

The SAME function must be used for training data and at run time.
Run order matters: specific patterns first, generic last.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from common.constants import HELPLINES

_TLDS = (
    r"(?:com|in|net|org|co|info|xyz|top|shop|online|site|live|club|app|link|io|me|ly|gl|gd|cc|"
    r"biz|store|tk|ml|ga|cf|gq|pw|ws|cn|ru|vip|bet|win|icu|cyou|buzz|today|support|help|"
    r"page|website|space|fun|tech|work|services|finance|bank|loan|money|gov|nic|ac|edu|ai|to|im|sh|tv|us|uk)"
)

PATTERNS: list[tuple[str, re.Pattern]] = [
    # UPI deep links before normal URLs
    ("UPI_LINK", re.compile(r"upi://[^\s]+", re.I)),
    ("URL", re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.I)),
    ("EMAIL", re.compile(r"\b[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+\b")),
    # UPI ID: handle@bank (no dot after @, so emails don't match)
    ("UPI", re.compile(r"(?<![\w.@])[\w.\-]{2,64}@[a-zA-Z]{2,32}(?![\w.@])")),
    # bare domains like sbi-kyc.in/verify (not part of an email)
    ("URL", re.compile(r"(?<![@\w.\-])(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+" + _TLDS +
                       r"(?![a-z0-9\-@])(?:/[^\s<>\"']*)?", re.I)),
    ("AADHAAR", re.compile(r"(?<!\d)[2-9]\d{3}[ \-]\d{4}[ \-]\d{4}(?!\d)")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    # international numbers (not +91)
    ("PHONE_INTL", re.compile(r"(?<![\w+])\+(?!91)\d{1,3}[ \-]?\(?\d{2,4}\)?[ \-]?\d{3,4}[ \-]?\d{3,5}(?!\d)")),
    # Indian mobile numbers: optional +91/91/0, starts 6-9, 10 digits (spaces/dashes allowed)
    ("PHONE", re.compile(r"(?<![\w])(?:\+?91[ \-]?|0)?[6-9]\d{2}[ \-]?\d{3}[ \-]?\d{4}(?!\d)")),
    ("PHONE", re.compile(r"(?<![\w])(?:\+?91[ \-]?|0)?[6-9]\d{4}[ \-]?\d{5}(?!\d)")),
    # amounts: ₹/rs/inr before or units after; lakh/crore/k; Hindi units
    ("AMOUNT", re.compile(
        r"(?:₹|\brs\.?|\binr\b|\brupees?\b)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakh|lac|crore|cr|k|hazaar|hazar|thousand|लाख|करोड़|हज़ार|हजार))?",
        re.I)),
    ("AMOUNT", re.compile(
        r"(?<![\w])\d[\d,]*(?:\.\d+)?\s?(?:lakh|lac|crore|cr|hazaar|hazar|thousand|rupees?|rs\b\.?|/-|लाख|करोड़|हज़ार|हजार|रुपये|रुपए)",
        re.I)),
    # long digit runs = account/card-like
    ("ACCOUNT", re.compile(r"(?<![\d\w])\d(?:[ \-]?\d){8,17}(?![\d\w])")),
    # OTP-like codes: 4-8 digits, not years, not part of dates/times
    ("CODE", re.compile(r"(?<![\d/\-:.\w])\d{4,8}(?![\d/\-:\w])")),
]


@dataclass
class EntityResult:
    text_model: str
    found: dict[str, list[str]] = field(default_factory=dict)

    def has(self, kind: str) -> bool:
        return bool(self.found.get(kind))

    def flags(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.found.items()}


def _keep_as_is(kind: str, value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if kind in ("CODE", "PHONE", "ACCOUNT") and digits in HELPLINES:
        return True  # 1930, 112 ... keep meaning
    if kind == "CODE" and len(digits) == 4 and 1950 <= int(digits) <= 2099:
        return True  # years
    return False


def extract(text: str) -> EntityResult:
    """`text` should already be normalized (engine.normalizer.normalize(...).clean)."""
    found: dict[str, list[str]] = {}
    out = text
    for kind, pat in PATTERNS:
        def _rep(m: re.Match, kind=kind) -> str:
            val = m.group(0)
            # strip trailing punctuation from URLs
            if kind == "URL":
                trail = re.search(r"[.,;:!?)\]]+$", val)
                if trail:
                    val = val[: trail.start()]
                    found.setdefault(kind, []).append(val)
                    return f"<{kind}>" + m.group(0)[len(val):]
            if _keep_as_is(kind, val):
                return val
            found.setdefault(kind, []).append(val)
            return f"<{kind}>"
        out = pat.sub(_rep, out)
    return EntityResult(text_model=out, found=found)


def prepare_for_model(raw_text: str):
    """normalize + extract in one call. Returns (NormResult, EntityResult)."""
    from engine.normalizer import normalize
    n = normalize(raw_text)
    e = extract(n.clean)
    return n, e


if __name__ == "__main__":
    tests = [
        "Pay ₹1,999 at sbi-kyc.in/verify or call +92 300 1234567",
        "Send 5000 rs to refund.help@ybl urgently. Contact 98765 43210",
        "Mera email ravi.k@gmail.com hai, call +91-9876543210",
        "Your OTP is 482913. Do not share. Call 1930 for fraud. Exam on 12/10/2026, fees 2026 batch",
        "Scan this: upi://pay?pa=abc@okaxis&am=4999",
        "Aadhaar 2345 6789 0123 and PAN ABCDE1234F, a/c 123456789012",
        "आपको 25 लाख का इनाम मिला है, ₹5000 प्रोसेसिंग फीस भेजें",
        "Visit https://www.incometax.gov.in/iec/foportal/. Thanks!",
        "Meeting at 10:30, room 4021",
    ]
    for t in tests:
        r = extract(t)
        print(t, "\n  ->", r.text_model, r.flags())
