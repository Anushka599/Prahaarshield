"""PrahaarShield identifier checks: phone numbers, UPI IDs, links (+ bank accounts against the registry).

Layers (most certain first):
  1 user's own lists (contact status: safe / blocked / not_saved)     -> only for the sender number
  2 Simulated I4C Suspect Registry (exact match)                      -> 'registry_hit'
  3 official lists (TRAI number series, helplines, bank/gov domains, UPI handles) -> 'official'
  4 India-specific rules (format, foreign code, look-alike domains, odd UPI handles ...) -> 'suspicious' / 'note'
  5 context (message text + conversation) is combined later in the Brain

Every finding is a CODE + params; the Brain renders it in English / Hindi / Marathi.
Risk per identifier: registry_hit > suspicious > note > official > unknown
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REG_DIR = Path(__file__).resolve().parents[1] / "registry"
OFFICIAL = json.load(open(REG_DIR / "official_lists.json", encoding="utf-8"))
_REG = json.load(open(REG_DIR / "suspect_registry_SIMULATED.json", encoding="utf-8"))
REGISTRY_LABEL = _REG["source_label"]
RISK_ORDER = {"registry_hit": 4, "suspicious": 3, "note": 2, "official": 1, "unknown": 0}

CLAIMS_ORG = re.compile(r"\b(bank|sbi|hdfc|icici|axis|kotak|rbi|kyc|yono|police|cbi|customs|court|ed\b|income ?tax|govt|government|"
                        r"sebi|npci|uidai|aadhaar|trai|telecom|cyber ?cell|crime branch)\b|बैंक|पुलिस|सीबीआई|बँक|पोलीस", re.I)


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def phone_key(raw: str) -> str:
    """Canonical key: '+<cc><number>' for international, '+91<10 digits>' for Indian mobiles, else digits.
    Masked demo numbers (with X) keep their X's so they can match the demo registry entries."""
    s = (raw or "").strip()
    if "x" in s.lower():
        return re.sub(r"[\s\-()]", "", s).upper()
    d = _digits(s)
    if s.startswith("+"):
        return "+" + d
    if len(d) == 12 and d.startswith("91"):
        return "+" + d
    if len(d) == 11 and d.startswith("0") and d[1] in "6789":
        return "+91" + d[1:]
    if len(d) == 10 and d[0] in "6789":
        return "+91" + d
    return d


def _domain_of(url: str) -> str:
    u = re.sub(r"^[a-z]+://", "", (url or "").strip().lower())
    u = u.split("/")[0].split("?")[0].split("#")[0]
    u = u.split("@")[-1].split(":")[0]
    return u[4:] if u.startswith("www.") else u


def _reg_index():
    idx = {}
    for e in _REG["entries"]:
        t, v = e["identifier_type"], e["value"]
        if t == "phone":
            k = phone_key(v)
        elif t == "upi":
            k = v.strip().lower()
        elif t == "url_domain":
            k = v.strip().lower()
        else:
            k = _digits(v)
        idx[(t, k)] = e
    return idx


REG = _reg_index()


def _lev(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 3
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _finding(code: str, risk: str, **params) -> dict:
    return {"code": code, "risk": risk, "params": params}


def _result(kind: str, value: str, findings: list[dict]) -> dict:
    risk = max((f["risk"] for f in findings), key=lambda r: RISK_ORDER[r], default="unknown")
    return {"type": kind, "value": value, "risk": risk, "findings": findings}


def _registry_finding(entry: dict) -> dict:
    return _finding("registry_hit", "registry_hit", count=entry["report_count"], scam_type=entry["scam_type"],
                    last=entry["last_reported"], state=entry["state"], source=REGISTRY_LABEL, risk_level=entry["risk_level"])


# ------------------------------------------------------------------ phone
def check_phone(raw: str, text: str = "", is_sender: bool = False, contact_status: str | None = None) -> dict:
    f = []
    key = phone_key(raw)
    if is_sender and contact_status == "blocked":
        f.append(_finding("contact_blocked", "suspicious"))
    elif is_sender and contact_status == "safe":
        f.append(_finding("contact_safe", "official"))
    elif is_sender and contact_status == "not_saved":
        f.append(_finding("contact_unknown", "note"))
    e = REG.get(("phone", key))
    if e:
        f.append(_registry_finding(e))
    d = _digits(raw)
    if "x" in (raw or "").lower():
        pass                                           # masked demo number: only the registry can judge it
    elif d in OFFICIAL["helplines"] or (not raw.strip().startswith("+") and d in OFFICIAL["helplines"]):
        f.append(_finding("helpline", "official", name=OFFICIAL["helplines"][d]))
    elif raw.strip().startswith("+") and not key.startswith("+91"):
        cc = next((c for c in sorted(OFFICIAL["country_codes"], key=len, reverse=True) if key[1:].startswith(c)), None)
        f.append(_finding("intl_number", "note", cc="+" + (cc or key[1:4]), country=OFFICIAL["country_codes"].get(cc, "another country")))
    else:
        local = d[2:] if (len(d) == 12 and d.startswith("91")) else d
        if local.startswith("1601") and len(local) == 10:
            f.append(_finding("series_1601", "official"))
        elif local.startswith("1600") and len(local) == 10:
            f.append(_finding("series_1600", "official"))
        elif local.startswith("140") and len(local) == 10:
            f.append(_finding("series_140", "note"))
        elif local.startswith("1800"):
            f.append(_finding("toll_free", "official"))
        elif len(local) == 10 and local[0] in "6789":
            if CLAIMS_ORG.search(text or ""):
                f.append(_finding("mobile_claims_org", "note"))
        elif len(local) == 11 and local.startswith("0"):
            f.append(_finding("landline", "note"))
        elif local:
            f.append(_finding("invalid_number", "suspicious", digits=len(local)))
    return _result("phone", raw, f)


# ------------------------------------------------------------------ UPI
UPI_RX = re.compile(r"^([a-z0-9.\-_]{2,256})@([a-z][a-z0-9]{1,64})$", re.I)


def check_upi(raw: str, text: str = "") -> dict:
    f = []
    v = (raw or "").strip().lower()
    if v.startswith("upi://"):
        m = re.search(r"pa=([^&\s]+)", v)
        v = m.group(1) if m else v
        if "am=" in raw.lower():
            f.append(_finding("upi_pay_link", "note"))
    e = REG.get(("upi", v))
    if e:
        f.append(_registry_finding(e))
    m = UPI_RX.match(v)
    if not m:
        f.append(_finding("upi_bad_format", "suspicious"))
        return _result("upi", raw, f)
    name, handle = m.groups()
    if handle not in OFFICIAL["upi_handles"]:
        f.append(_finding("upi_unknown_handle", "suspicious", handle="@" + handle))
    words = [w for w in OFFICIAL["upi_suspicious_words"] if w in name]
    if words:
        f.append(_finding("upi_suspicious_words", "suspicious", words=", ".join(words[:3])))
    if CLAIMS_ORG.search(text or "") and re.search(r"\d{6,}|^[a-z]+\.?[a-z]*\d*$", name) and not words:
        f.append(_finding("upi_personal_for_org", "suspicious"))
    if not f:
        f.append(_finding("upi_known_handle", "official", handle="@" + handle))
    return _result("upi", raw, f)


# ------------------------------------------------------------------ links
def check_link(raw: str, text: str = "") -> dict:
    f = []
    url = (raw or "").strip()
    low = url.lower()
    dom = _domain_of(url)
    full = re.sub(r"^[a-z]+://", "", low).split("?")[0].rstrip("/")
    e = REG.get(("url_domain", dom)) or REG.get(("url_domain", full))
    if e:
        f.append(_registry_finding(e))
    official = dom in OFFICIAL["official_domains"] or any(dom == s[1:] or dom.endswith(s) for s in OFFICIAL["official_domain_suffixes"]) \
        or any(dom.endswith("." + o) for o in OFFICIAL["official_domains"])
    if any(dom == d or full.startswith(d) for d in OFFICIAL["invite_domains"]):
        f.append(_finding("link_invite", "note", domain=dom))
    elif official:
        f.append(_finding("link_official", "official", domain=dom))
    else:
        if dom in OFFICIAL["shorteners"]:
            f.append(_finding("link_shortener", "suspicious", domain=dom))
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", dom):
            f.append(_finding("link_ip", "suspicious"))
        if "xn--" in dom or re.search(r"[^\x00-\x7f]", dom):
            f.append(_finding("link_punycode", "suspicious"))
        tld = dom.rsplit(".", 1)[-1] if "." in dom else ""
        if tld in OFFICIAL["risky_tlds"]:
            f.append(_finding("link_risky_tld", "suspicious", tld="." + tld))
        if re.search(r"\.(apk|exe|bat|scr|msi)(\b|$)", full):
            f.append(_finding("link_apk", "suspicious"))
        labels = re.split(r"[.\-_]", dom.rsplit(".", 1)[0])
        hit = None
        for b, name in OFFICIAL["brands"].items():
            if any(lbl == b or (len(b) >= 4 and b in lbl) for lbl in labels):
                hit = ("link_brand_misuse", name); break
        if not hit:
            for b, name in OFFICIAL["brands"].items():
                if len(b) >= 4 and any(len(lbl) >= 4 and 0 < _lev(lbl, b) <= (1 if len(b) <= 5 else 2) for lbl in labels):
                    hit = ("link_lookalike", name); break
        if not hit:                                   # 3-letter brands (sbi, pnb, rbi, cbi): one letter off + banking words nearby
            bankish = any(w in dom for w in ("bank", "netbanking", "login", "kyc", "verify", "yono", "account", "reward", "refund"))
            for b, name in OFFICIAL["brands"].items():
                if len(b) == 3 and bankish and any(len(lbl) == 3 and _lev(lbl, b) == 1 for lbl in labels):
                    hit = ("link_lookalike", name); break
        if hit:
            f.append(_finding(hit[0], "suspicious", brand=hit[1], domain=dom))
        if low.startswith("http://") and not f:
            f.append(_finding("link_http", "note"))
        if "@" in re.sub(r"^[a-z]+://", "", low).split("/")[0]:
            f.append(_finding("link_userinfo", "suspicious"))
        if not f:
            f.append(_finding("link_unknown", "note", domain=dom))
    return _result("link", raw, f)


def check_account(raw: str) -> dict | None:
    e = REG.get(("bank_account", _digits(raw)))
    return _result("bank_account", raw, [_registry_finding(e)]) if e else None


# ------------------------------------------------------------------ all identifiers in one message
def check_message(found: dict, text: str) -> list[dict]:
    """found = entities.extract(...).found  ({'URL': [...], 'UPI': [...], 'PHONE': [...], 'PHONE_INTL': [...], 'ACCOUNT': [...]})."""
    out = []
    for u in found.get("URL", []):
        out.append(check_link(u, text))
    for u in found.get("UPI", []):
        out.append(check_upi(u, text))
    for p in found.get("PHONE", []) + found.get("PHONE_INTL", []):
        out.append(check_phone(p, text))
    for a in found.get("ACCOUNT", []):
        r = check_account(a)
        if r:
            out.append(r)
    return out


if __name__ == "__main__":
    tests = [check_phone("+92 300 1234567"), check_phone("1601234567"), check_phone("+91 98220 11111", "SBI KYC team here"),
             check_phone("+91 70XXX 45210"), check_phone("12345"), check_phone("1930"),
             check_upi("rbi.safe.ac@ybl", "RBI safe account"), check_upi("ramesh123@okaxis"), check_upi("kyc.update7@xyzpay", "SBI KYC"),
             check_link("https://sbi-yono-kyc-update.in/verify"), check_link("https://www.onlinesbi.sbi/"), check_link("http://hdfcbnak.com/login"),
             check_link("bit.ly/3xYz"), check_link("https://sbi.bank.in"), check_link("http://192.168.1.4/pay.apk"), check_link("chat.whatsapp.com/AbC"),
             check_link("https://sebi-reg-advisory.top/join")]
    for t in tests:
        print(f"{t['type']:5s} {t['value'][:40]:40s} {t['risk']:12s} {[x['code'] for x in t['findings']]}")
