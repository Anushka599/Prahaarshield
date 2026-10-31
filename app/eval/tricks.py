"""Adversarial 'trick' transforms (what scammers do to dodge filters). Used by run_eval.py."""
import random

HOMO = {"a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х", "i": "і", "y": "у"}   # Latin -> Cyrillic look-alikes
ZW = "\u200b"
EMOJI = ["🔥", "💰", "✅", "🙏", "😊", "⚡", "📲", "🎉"]
KEY = ["otp", "kyc", "pin", "account", "bank", "transfer", "police", "arrest", "loan", "fee", "deposit", "profit", "task", "urgent"]


def homoglyph(t, rnd):
    return "".join(HOMO[ch] if ch in HOMO and rnd.random() < 0.35 else ch for ch in t)


def zero_width(t, rnd):
    return "".join(ch + (ZW if ch.isalpha() and rnd.random() < 0.25 else "") for ch in t)


def spaced(t, rnd):
    out = t
    for k in KEY:
        idx = out.lower().find(k)
        if idx >= 0:
            out = out[:idx] + " ".join(out[idx:idx + len(k)]) + out[idx + len(k):]
    return out


def emoji_spam(t, rnd):
    w = t.split()
    return " ".join(x + (rnd.choice(EMOJI) if rnd.random() < 0.3 else "") for x in w)


def leet(t, rnd):
    return t.replace("o", "0").replace("O", "0").replace("i", "1").replace("a", "@")


def shout(t, rnd):
    return t.upper()


TRICKS = {"homoglyph": homoglyph, "zero_width": zero_width, "spaced_letters": spaced, "emoji_spam": emoji_spam, "leetspeak": leet, "all_caps": shout}
