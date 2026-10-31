"""PrahaarShield style engine (v3.3): makes WhatsApp-style variety -  used for BOTH scam and normal messages.

Why: real people write the same thing in many ways (no emojis / a few / MANY, slang, typos, all caps, no punctuation,
Hinglish vs Marathi particles).  If one style appears mostly in scams, the model learns "style = scam" (a shortcut).
So every profile is applied with the same probability to scam AND benign rows; the label never decides the style.

Run:  python make_style_aug.py   (writes style_aug_v33.jsonl next to the other datasets; prepare_v3.py picks it up)
Amounts, numbers, links and phone numbers are never changed.
"""
from __future__ import annotations

import random
import re

EMO = {"money": ["💰", "💸", "🤑", "💵"], "urgent": ["⏰", "🚨", "⚠️", "‼️", "🔥"], "sad": ["😢", "🙏", "😟", "🥺", "😭"],
       "happy": ["😂", "😄", "👍", "😊", "🎉", "🤣", "😁"], "neutral": ["🙂", "👀", "✅", "📌", "👇"]}
SLANG = {"hinglish": ["yaar", "bhai", "bro", "na", "re", "boss"], "en": ["bro", "dude", "pls", "ok?", "ya"],
         "mr": ["re", "ga", "na", "bara", "ki", "bhau"], "hi_deva": ["यार", "भाई", "ना", "जी"], "mr_deva": ["रे", "गं", "ना", "बरं", "ना रे"]}
ABBR = [(r"\bplease\b", ["pls", "plz", "plzz"]), (r"\byou\b", ["u"]), (r"\byour\b", ["ur"]), (r"\bare\b", ["r"]), (r"\bokay\b", ["ok", "okk"]),
        (r"\bwhat\b", ["wht", "wat"]), (r"\bbecause\b", ["coz", "bcz"]), (r"\btomorrow\b", ["tmrw", "kal"]), (r"\bmessage\b", ["msg"]),
        (r"\bthanks\b", ["thx", "thnx"]), (r"\bkar raha\b", ["kr rha"]), (r"\bkya\b", ["kya", "kyaa"]), (r"\bhai\b", ["h", "hai"])]
PROTECT = re.compile(r"https?://\S+|[\w.-]+@[\w]+|₹\s?[\d,]+|\+?\d[\d\s-]{5,}\d|\b\d+\b|[\w-]+\.(in|com|net|org|co|top|app)\b", re.I)
PROFILES = {   # name: (emoji level, slang, abbreviations, typo rate, casing, punctuation)
    "plain":       (0, False, False, 0.00, "keep", "keep"),
    "lazy":        (0, False, True, 0.05, "lower", "strip"),
    "few_emoji":   (1, True, False, 0.00, "keep", "keep"),
    "chatty":      (2, True, True, 0.04, "lower", "dots"),
    "emoji_heavy": (3, True, False, 0.02, "keep", "bang"),
    "shouty":      (1, False, False, 0.00, "upper_words", "bang"),
    "typo":        (0, True, True, 0.10, "lower", "strip"),
}


def _is_dev(t: str) -> bool:
    return len(re.findall(r"[\u0900-\u097F]", t)) > len(re.findall(r"[A-Za-z]", t))


def _mood(text: str) -> str:
    t = text.lower()
    if re.search(r"₹|\bpaise|money|pay|send|bhej|पैसे|पाठव", t): return "money"
    if re.search(r"urgent|jaldi|turant|now|abhi|लगेच|पटकन|तुरंत|freeze|block", t): return "urgent"
    if re.search(r"please|sorry|plz|help|मदत|मदद|🙏", t): return "sad"
    if re.search(r"haha|😂|thanks|party|happy|congrat|बधाई|अभिनंदन", t): return "happy"
    return "neutral"


def _protect(text: str):
    keep = []
    def sub(m):
        keep.append(m.group(0)); return f"\x00{len(keep) - 1}\x00"
    return PROTECT.sub(sub, text), keep


def _restore(text: str, keep):
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)


def _typo(word: str, rng: random.Random) -> str:
    if len(word) < 4 or not word.isascii() or not word.isalpha():
        return word
    i = rng.randrange(1, len(word) - 1)
    op = rng.choice(["drop", "double", "swap"])
    if op == "drop": return word[:i] + word[i + 1:]
    if op == "double": return word[:i] + word[i] + word[i:]
    return word[:i - 1] + word[i] + word[i - 1] + word[i + 1:]


def stylize(text: str, language: str, profile: str, rng: random.Random) -> str:
    emo, slang, abbr, typo, case, punct = PROFILES[profile]
    body, keep = _protect(text)
    if abbr and not _is_dev(body):
        for rx, outs in ABBR:
            if rng.random() < 0.7:
                body = re.sub(rx, lambda m: rng.choice(outs), body, count=1, flags=re.I)
    if typo:
        body = " ".join(_typo(w, rng) if rng.random() < typo else w for w in body.split(" "))
    if case == "lower" and not _is_dev(body):
        body = body.lower()
    elif case == "upper_words":
        ws = body.split(" "); idx = [i for i, w in enumerate(ws) if w.isascii() and len(w) > 3]
        for i in rng.sample(idx, min(len(idx), 2)): ws[i] = ws[i].upper()
        body = " ".join(ws)
    if punct == "strip":
        body = re.sub(r"[.,!?;:।]+(\s|$)", r"\1", body)
    elif punct == "dots":
        body = re.sub(r"[.।]\s*$", "", body) + rng.choice(["...", "..", " ..."])
    elif punct == "bang":
        body = re.sub(r"[.।]\s*$", "", body) + rng.choice(["!!", "!!!", "!?"])
    if slang:
        key = "mr_deva" if (language == "mr" and _is_dev(body)) else ("hi_deva" if _is_dev(body) else language)
        pool = SLANG.get(key, SLANG["en"])
        p = rng.choice(pool)
        body = (body.rstrip() + " " + p) if rng.random() < 0.6 else (p + " " + body)
    if emo:
        pool = EMO[_mood(text)] + EMO["neutral"]
        n = {1: rng.randint(1, 2), 2: rng.randint(2, 3), 3: rng.randint(4, 7)}[emo]
        chosen = [rng.choice(pool) for _ in range(n)]
        if emo == 3 and rng.random() < 0.5:
            words = body.split(" ")
            for e in chosen[: len(chosen) // 2]:
                words.insert(rng.randrange(0, len(words) + 1), e)
            body = " ".join(words) + " " + "".join(chosen[len(chosen) // 2:])
        else:
            body = body.rstrip() + " " + "".join(chosen)
    return _restore(body, keep).strip()


def random_profile(rng: random.Random) -> str:
    return rng.choices(list(PROFILES), weights=[2, 2, 3, 3, 2, 1, 2])[0]
