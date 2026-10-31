"""Normalizer: undo common scammer text tricks.

Returns two versions of the text:
  original -> kept for display
  clean    -> used by the model
plus a list of tricks found. `obfuscation_detected` is True only for
STRONG tricks (look-alike letters, invisible characters), because genuine
messages almost never contain them.

Order of operations (matters!):
  1 detect fancy fonts  2 Devanagari digits -> ASCII  3 defang links
  4 invisible chars     5 NFKC                        6 look-alike letters
  7 spaced letters      8 whitespace
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# --- invisible characters -------------------------------------------------
# Always-suspicious invisibles (never needed in normal chat text)
_ALWAYS_INVISIBLE = re.compile(
    "[\u200b\u2060\ufeff\u00ad\u180e\u200e\u200f\u202a-\u202e\u2066-\u2069]"
)
# ZWJ / ZWNJ are LEGIT in Devanagari and emoji sequences -> only suspicious between Latin letters
_ZWJ_BETWEEN_LATIN = re.compile(r"(?<=[A-Za-z])[\u200c\u200d]+(?=[A-Za-z])")

# --- look-alike letters (Cyrillic / Greek -> Latin) -----------------------
CONFUSABLES = {
    # Cyrillic lowercase
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h", "ӏ": "l", "ԛ": "q", "ԝ": "w",
    # Cyrillic uppercase
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O",
    "Р": "P", "С": "C", "Т": "T", "Х": "X", "Ѕ": "S", "І": "I", "Ј": "J", "У": "Y",
    # Greek
    "ο": "o", "ν": "v", "ρ": "p", "α": "a", "ι": "i", "κ": "k",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K",
    "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
}
_CONF_SET = set(CONFUSABLES)

# --- fancy fonts ----------------------------------------------------------
def _is_fancy(ch: str) -> bool:
    cp = ord(ch)
    return (0x1D400 <= cp <= 0x1D7FF      # mathematical bold/italic/script letters
            or 0xFF01 <= cp <= 0xFF5E     # full-width ASCII
            or 0x24B6 <= cp <= 0x24E9     # circled letters
            or 0x1F130 <= cp <= 0x1F189)  # squared/negative squared letters

# --- Devanagari digits ----------------------------------------------------
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# --- defanged links -------------------------------------------------------
_DEFANG = [
    (re.compile(r"hxxps", re.I), "https"),
    (re.compile(r"hxxp", re.I), "http"),
    (re.compile(r"\[\.\]|\(\.\)|\{\.\}|\[dot\]|\(dot\)", re.I), "."),
    (re.compile(r"\[:\]"), ":"),
]

# --- spaced letters: "K Y C", "O.T.P", "a-c-c-o-u-n-t" ----------------------
_SPACED = re.compile(r"(?<![A-Za-z])((?:[A-Za-z][ .\-_*]{1,2}){2,}[A-Za-z])(?![A-Za-z])")
_SPACED_SHORT = re.compile(r"(?<![A-Za-z])((?:[A-Za-z][ .\-_*]){1,}[A-Za-z])(?![A-Za-z])")

_MULTI_SPACE = re.compile(r"[ \t\u00a0\u202f]+")
_MULTI_NL = re.compile(r"\n{2,}")
_LATIN = re.compile(r"[A-Za-z]")


@dataclass
class NormResult:
    original: str
    clean: str
    tricks: list[str] = field(default_factory=list)

    @property
    def obfuscation_detected(self) -> bool:
        return any(t in ("homoglyph", "invisible_chars") for t in self.tricks)

    def to_dict(self) -> dict:
        return {"clean": self.clean, "tricks": self.tricks,
                "obfuscation_detected": self.obfuscation_detected}


def _fix_homoglyphs(text: str) -> tuple[str, bool]:
    """Replace look-alike letters inside tokens that are Latin-context.

    A token is fixed if it mixes Latin + confusable letters ("ЅBI"), or if it is
    made ONLY of confusable letters while the message is mostly Latin ("ЅВІ").
    Devanagari is never touched.
    """
    latin_chars = len(_LATIN.findall(text))
    other_letters = sum(1 for c in text if c.isalpha() and not _LATIN.match(c) and c not in _CONF_SET)
    mostly_latin = latin_chars >= other_letters
    changed = False
    out = []
    for tok in re.split(r"(\s+)", text):
        if any(c in _CONF_SET for c in tok):
            letters = [c for c in tok if c.isalpha()]
            has_latin = any(_LATIN.match(c) for c in letters)
            only_conf = letters and all(c in _CONF_SET for c in letters)
            if has_latin or (only_conf and mostly_latin):
                tok = "".join(CONFUSABLES.get(c, c) for c in tok)
                changed = True
        out.append(tok)
    return "".join(out), changed


def normalize(text: str) -> NormResult:
    original = text if isinstance(text, str) else ""
    t = original
    tricks: list[str] = []

    # 1 fancy fonts (detect before NFKC turns them into plain letters)
    if any(_is_fancy(c) for c in t):
        tricks.append("fancy_font")

    # 2 Devanagari digits -> ASCII digits (so entity extraction sees them)
    t = t.translate(_DEV_DIGITS)

    # 3 defanged links
    before = t
    for pat, rep in _DEFANG:
        t = pat.sub(rep, t)
    if t != before:
        tricks.append("defanged_link")

    # 4 invisible characters
    before = t
    t = _ALWAYS_INVISIBLE.sub("", t)
    t = _ZWJ_BETWEEN_LATIN.sub("", t)
    if t != before:
        tricks.append("invisible_chars")

    # 5 NFKC: fancy/full-width letters -> normal
    t = unicodedata.normalize("NFKC", t)

    # 6 look-alike letters
    t, changed = _fix_homoglyphs(t)
    if changed:
        tricks.append("homoglyph")

    # 7 spaced letters ("K Y C" -> "KYC")
    def _join(m: re.Match) -> str:
        letters = re.sub(r"[ .\-_*]", "", m.group(1))
        # join only "K Y C"-style (all caps, >=3) or long runs (>=5 letters).
        # keeps normal texting like "u r a" untouched
        if (letters.isupper() and len(letters) >= 3) or len(letters) >= 5:
            return letters
        return m.group(1)
    before = t
    t = _SPACED.sub(_join, t)
    if t != before:
        tricks.append("spaced_letters")
        # the sender is clearly spacing letters on purpose -> also join short words ("t h e", "t o")
        t = _SPACED_SHORT.sub(lambda m: re.sub(r"[ .\-_*]", "", m.group(1)), t)

    # 8 whitespace
    t = _MULTI_SPACE.sub(" ", t)
    t = _MULTI_NL.sub("\n", t)
    t = "\n".join(line.strip() for line in t.split("\n")).strip()

    return NormResult(original=original, clean=t, tricks=tricks)


if __name__ == "__main__":
    samples = [
        "Your ЅBI account is blocked. Update K Y C now",
        "O\u200bT\u200bP share karo turant",
        "𝐔𝐫𝐠𝐞𝐧𝐭: visit hxxps://sbi-kyc[.]in/verify",
        "आपका खाता ब्लॉक हो जाएगा, ₹५००० जमा करें",
        "Happy birthday beta 🎂👨\u200d👩\u200d👧",
    ]
    for s in samples:
        r = normalize(s)
        print(repr(s), "\n  ->", repr(r.clean), r.tricks, "obf=", r.obfuscation_detected)
