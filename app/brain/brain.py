"""PrahaarShield Brain v2 (text only).

Inputs : M1 message results (calibrated) · M7 conversation result · identifier findings · hard rules · context signals
Output : severity L0-L4 per message and per chat, stage timeline, explanations (en / hi / mr), SOS report, evidence pack.

Fusion = transparent rules (no black box):
  1 text level from the calibrated scam probability: <0.30 L0 · <threshold L1 · <0.80 L2 · >=0.80 L3
  2 hard-rule floor (OTP ask, screen-share/APK, UPI-PIN collect, gift codes, 'safe account') -> >= L3
  3 identifiers: registry hit -> +1 (>= L2) · rule-based 'suspicious' -> +1 when text >= L1 · notes/official -> explanation only
  4 context (account type / contacts): at most +-1, never below a hard-rule floor, never creates L3+ from context alone
  5 chat level = max(message levels, M7 chat score); L4 when >= L3 AND the scam has reached the DEMAND stage
  6 unreliable text (unsupported language / < 3 words) is capped at L1 unless a hard rule or registry hit applies
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

T = json.load(open(Path(__file__).with_name("templates.json"), encoding="utf-8"))
LEVELS = {i: n for i, n in enumerate(T["levels"]["en"])}
HARD_RULES = {"cred_ask", "apk", "upi_pin_collect", "gift_codes", "safe_account", "wa_code"}
from brain.reasoning import PRESSURE, S as RS, chat_facts, compose_chat, message_notes, otp_kind, tactics, trusted

TYPE_MIN_CONF = 0.60
# the USER's own messages: sharing a code, saying they paid, or installing an app inside an already-risky chat
VICTIM = re.compile(r"\b(otp|code|pin)\b[^\n]{0,15}\b\d{4,8}\b|^\W*(sent:?\s*)?\d{6}\W*$|\b(paid|transferred|sent the money|done,? paid|bhej diya|bhej diye|bhar diya|bhar diye|pay kar diya|transfer kar diya|"
                    r"paise bharle|installed the app|install kar liya|anydesk)\b|ओटीपी\s*\d{4,8}|भर दिए|भेज दिए|ट्रांसफर कर दिया|भरले|पाठवले|OTP\s*\d{4,8}", re.I)          # below this the app says "scam" and does not name a type (honest confidence)
CLAIMS_ORG = re.compile(r"\b(bank|sbi|hdfc|icici|axis|kotak|rbi|kyc|yono|police|cbi|customs|court|income ?tax|government|sebi|"
                        r"uidai|aadhaar|trai|amazon|flipkart|paytm|phonepe)\b|बैंक|पुलिस|बँक|पोलीस", re.I)


def L(group: str, key: str, lang: str, **p) -> str:
    entry = T[group][key]
    s = entry.get(lang) or entry["en"]
    try:
        return s.format(**p)
    except (KeyError, IndexError):
        return s


def level_name(lvl: int, lang: str = "en") -> str:
    return T["levels"].get(lang, T["levels"]["en"])[lvl]


def type_name(t: str | None, lang: str = "en") -> str:
    return L("types", t, lang) if t in T["types"] else (t or "")


# ------------------------------------------------------------------ per message
def text_level(a: dict, threshold: float = 0.5) -> int:
    p = a["p_scam"]
    t2 = max(0.80, threshold + 0.5 * (1 - threshold))     # Dangerous starts here; Suspicious = [threshold, t2)
    lvl = 0 if p < 0.30 else 1 if p < threshold else 2 if p < t2 else 3
    hard = HARD_RULES & set(a.get("rules", []))
    if hard:                                   # OTP / PIN / APK / gift codes / "safe account": always at least Dangerous
        lvl = max(lvl, 3)
    if not a.get("text_reliable", True) and not hard:
        lvl = min(lvl, 1)
    return lvl


def message_level(a: dict, threshold: float = 0.5, ctx: dict | None = None) -> int:
    lvl = text_level(a, threshold)
    rules = set(a.get("rules", []))
    hard = bool(HARD_RULES & rules)
    if "cred_ask" in rules and trusted(ctx) and not (HARD_RULES & rules - {"cred_ask"}):
        text = a.get("clean_text") or ""
        kind, tac = otp_kind(text), tactics(text)
        if not tac & (PRESSURE | {"pay_ask"}):            # a family member asking for a code, with no pressure or money
            if kind == "delivery":
                lvl, hard = min(lvl, 1), False            # delivery / order OTP at home: normal
            elif kind == "unknown":
                lvl, hard = min(lvl, 2), False            # unclear code from a contact: note it, no alarm
            # bank / UPI / WhatsApp codes stay Dangerous even from contacts (account takeover)
    ids = a.get("identifiers", [])
    if any(i["risk"] == "registry_hit" for i in ids):
        lvl = max(lvl + 1, 2)
    elif any(i["risk"] == "suspicious" for i in ids) and lvl >= 1:
        lvl += 1
    if ctx:
        acc, cs = ctx.get("account_type", "general"), ctx.get("contact_status")
        if lvl >= 1 and (acc in ("fraud", "regional_scam") or (cs == "blocked" and ctx.get("contacts_permission"))):
            lvl += 1
        if acc == "business" and lvl >= 1 and _business_mismatch(a, ctx):
            lvl += 1
        sc = ctx.get("sender_check")
        if sc and sc.get("risk") == "registry_hit" and lvl >= 1:
            lvl += 1
        if cs == "safe" and ctx.get("contacts_permission") and lvl < 3:
            lvl = max(lvl - 1, 3 if hard else 0)
    return max(0, min(lvl, 3))


def _business_mismatch(a: dict, ctx: dict) -> bool:
    m = CLAIMS_ORG.search(a.get("clean_text", "") or "")
    return bool(m) and m.group(0).lower() not in (ctx.get("name") or "").lower()


def stage_of(a: dict) -> str | None:
    pl = a["pillars"]
    if pl["P_CRED"] >= .5 or pl["P_RESOURCE"] >= .5 or (HARD_RULES & set(a.get("rules", []))):
        return "demand"
    if pl["P_STAKES"] >= .5 or pl["P_CONTROL"] >= .5:
        return "pressure"
    if pl["P_IDENTITY"] >= .5 or pl["P_SITUATION"] >= .5:
        return "approach"
    return None


# ------------------------------------------------------------------ rendering helpers
def render_identifier(r: dict, lang: str) -> list[tuple[str, str]]:
    """-> [(kind, text)] where kind is 'flag' (red flag) or 'fact'."""
    out = []
    for f in r["findings"]:
        p = dict(f["params"], value=r["value"])
        if f["code"] == "registry_hit":
            p["scam_type"] = type_name(p.get("scam_type"), lang)
        txt = L("findings", f["code"], lang, **p) if f["code"] in T["findings"] else f["code"]
        out.append(("flag" if f["risk"] in ("registry_hit", "suspicious") else "fact", txt))
    return out


def context_lines(ctx: dict | None, lang: str, a: dict | None = None) -> list[tuple[str, str]]:
    if not ctx:
        return []
    out = []
    acc = ctx.get("account_type", "general")
    if acc == "scam":
        out.append(("flag", L("context", "account_scam", lang)))
    elif acc == "fraud":
        out.append(("flag", L("context", "account_fraud", lang)))
    elif acc == "regional_scam":
        out.append(("flag", L("context", "account_regional_scam", lang)))
    elif acc == "business":
        if a is not None and _business_mismatch(a, ctx):
            out.append(("flag", L("context", "account_business_mismatch", lang, name=ctx.get("name", ""))))
        else:
            out.append(("fact", L("context", "account_business", lang)))
    if ctx.get("chat_type") == "group":
        out.append(("fact", L("context", "group", lang)))
    sc = ctx.get("sender_check")
    if sc:
        out += render_identifier(sc, lang)
    return out


def explain_message(a: dict, lang: str = "en", threshold: float = 0.5, ctx: dict | None = None) -> dict:
    lvl = message_level(a, threshold, ctx)
    flags, facts = [], []
    if not a.get("text_reliable", True):
        facts.append(L("what", "unreliable", lang))
    if lvl >= 2:
        flags += [L("pillars", k, lang) for k, v in a["pillars"].items() if v >= 0.5]
        flags += [L("rules", r, lang) for r in a.get("rules", []) if r in T["rules"]]
        if a.get("obfuscation_detected"):
            flags.append(L("rules", "obfuscation", lang))
    for r in a.get("identifiers", []):
        for kind, txt in render_identifier(r, lang):
            (flags if kind == "flag" else facts).append(txt)
    for kind, txt in context_lines(ctx, lang, a):
        if kind == "flag" and lvl >= 2:
            flags.insert(0, txt)
        elif kind == "fact" and lvl >= 1:
            facts.append(txt)
    mflags, mfacts = message_notes(a.get("clean_text") or "", lang, lvl)
    flags += mflags
    facts = mfacts + facts
    if "cred_ask" in a.get("rules", []) and trusted(ctx) and otp_kind(a.get("clean_text") or "") == "delivery" and lvl < 2:
        facts.append(RS["otp_delivery"].get(lang, RS["otp_delivery"]["en"]))
    typed = a["scam_type"] in T["what"] and a.get("type_conf", 1.0) >= TYPE_MIN_CONF
    if lvl >= 2:
        what = L("what", a["scam_type"], lang) if typed else L("what", "generic", lang)
    else:
        what = L("what", "safe", lang)
    return {"level": lvl, "label": level_name(lvl, lang), "what": what, "red_flags": _dedupe(flags), "facts": _dedupe(facts),
            "highlights": a.get("highlights", []) if lvl >= 2 else [], "score": a["p_scam"],
            "scam_type": a["scam_type"] if (lvl >= 2 and typed) else None, "scam_type_name": type_name(a["scam_type"], lang) if (lvl >= 2 and typed) else None}


def _dedupe(xs):
    seen, out = set(), []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ------------------------------------------------------------------ per chat
def _conv_level(p: float, threshold: float) -> int:
    """Conversation score is re-scaled by the conversation engine (0.5 = alert), so fixed cut-points are used."""
    return 0 if p < 0.30 else 1 if p < 0.50 else 2 if p < 0.80 else 3


def assess_chat(messages: list[dict], threshold: float = 0.5, ctx: dict | None = None, conv: dict | None = None) -> dict:
    """messages: [{id, direction, text, analysis}] oldest -> newest. conv: M7 output for the chat (or None)."""
    inc = [m for m in messages if m.get("direction") == "in" and m.get("analysis")]
    reasons = []
    if not inc:
        lvl = 2 if ctx and ctx.get("account_type") == "scam" and messages else 0
        return {"level": lvl, "label": LEVELS[lvl], "checked": bool(messages), "scam_type": None, "flagged": [], "stage": None,
                "reasons": ["account_scam"] if lvl else [], "conv": conv}
    lv = [message_level(m["analysis"], threshold, ctx) for m in inc]
    texts = [m["analysis"].get("clean_text") or m.get("text") or "" for m in inc]
    tacs = [tactics(t) for t in texts]
    for i, m in enumerate(inc):                        # short messages ("send fast", "otp send kar") are judged with the chat
        rules = set(m["analysis"].get("rules", []))
        if len(texts[i].split()) <= 6 and lv[i] <= 1 and ("pay_ask" in tacs[i] or "cred_ask" in rules):
            prev = range(max(0, i - 4), i)
            if any(lv[j] >= 2 for j in prev) or len(set().union(*[tacs[j] for j in prev]) & PRESSURE) >= 2:
                lv[i] = 3 if "cred_ask" in rules else 2
                if "short_in_context" not in reasons:
                    reasons.append("short_in_context")
    level = max(lv)
    F = chat_facts(messages, ctx)
    if F["money_requests"] >= 2 and F["pressure"] >= 2:          # repeated money asks + (urgency/threat/blocking/secrecy/escalation)
        if level < 3:
            reasons.append("money_pressure")
        level = max(level, 3)
    elif F["money_requests"] >= 1 and F["blocking"] and level < 2:  # stops you checking while asking for money
        level = 2
        reasons.append("verification_blocked")
    flagged = [m["id"] for m, l in zip(inc, lv) if l >= 2]          # (lv already includes context-raised short messages)
    if conv and conv.get("p_scam") is not None:
        cl = _conv_level(conv["p_scam"], threshold)
        if cl > level and level >= 1:          # the conversation view can raise, never create an alert from nothing
            level = cl
            reasons.append("conversation_model")
    stages = [stage_of(m["analysis"]) if l >= 2 else None for m, l in zip(inc, lv)]
    recent = stages[-6:]
    risky = sum(1 for l in lv if l >= 2)
    strong = any((HARD_RULES & set(m["analysis"].get("rules", []))) or any(i["risk"] == "registry_hit" for i in m["analysis"].get("identifiers", []))
                 for m, l in zip(inc[-6:], lv[-6:]) if l >= 2)
    # the scam has reached its demand AND the evidence is more than one stray message (or is a hard rule / registry hit)
    rule_demand = "demand" in recent and (risky >= 2 or strong)
    conv_demand = bool(conv and conv.get("stage") == "demand" and conv.get("p_scam", 0) >= 0.5)
    if level >= 3 and (rule_demand or conv_demand):
        level = 4
        reasons.append("demand_stage")
    if level >= 2:
        first_risky = next((m["id"] for m, l in zip(inc, lv) if l >= 2), None)
        after = False
        for m in messages:
            if m["id"] == first_risky: after = True
            if after and m.get("direction") == "out" and VICTIM.search(m.get("text") or ""):
                level = 4
                reasons.append("victim_action")
                F["victim_action"] = True
                break
    if ctx and ctx.get("account_type") in ("fraud", "regional_scam") and inc and level < 1:
        level = 1                              # a reported account is never shown as plain "Safe" (but never Dangerous on its own)
    if ctx and ctx.get("account_type") == "scam" and level < 2:
        level = 2
        reasons.append("account_scam")
    if ctx and (ctx.get("sender_check") or {}).get("risk") == "registry_hit" and level < 2:
        level = 2
        reasons.append("sender_registry")
    votes, confs = Counter(), {}
    for m, l in zip(inc, lv):
        if l >= 2:
            votes[m["analysis"]["scam_type"]] += m["analysis"]["p_scam"]
            confs.setdefault(m["analysis"]["scam_type"], []).append(m["analysis"].get("type_conf", 1.0))
    stype = votes.most_common(1)[0][0] if votes else (conv.get("scam_type") if conv and level >= 2 else None)
    if stype in confs and sum(confs[stype]) / len(confs[stype]) < TYPE_MIN_CONF:
        stype = None                                   # unsure which type: the app says "scam" without naming one
    cur_stage = (conv or {}).get("stage") or next((s for s in reversed(stages) if s), None)
    return {"level": level, "label": LEVELS[level], "checked": True, "scam_type": stype, "flagged": flagged,
            "stage": cur_stage if level >= 2 else None, "reasons": reasons, "conv": conv, "_facts": F,
            "_sender_check": (ctx or {}).get("sender_check")}


def banner_text(chat: dict, lang: str = "en") -> str | None:
    lvl = chat["level"]
    if lvl < 2:
        return None
    if lvl == 2 and not chat.get("flagged"):
        if "account_scam" in chat.get("reasons", []):
            return "🟡 " + L("context", "account_scam", lang)
        if "sender_registry" in chat.get("reasons", []) and chat.get("_sender_check"):
            flags = [t for k, t in render_identifier(chat["_sender_check"], lang) if k == "flag"]
            if flags:
                return "🟡 " + flags[0]
    t = type_name(chat.get("scam_type"), lang) or {"en": "scam", "hi": "स्कैम", "mr": "स्कॅम"}.get(lang, "scam")
    txt = {"en": {4: f"🔴 Scam in progress: likely {t} scam. Tap for help", 3: f"🟠 Dangerous: likely {t} scam. Tap to see why",
                  2: "🟡 Suspicious messages in this chat. Tap to see why"},
           "hi": {4: f"🔴 स्कैम चल रहा है: शायद {t} स्कैम। मदद के लिए टैप करें", 3: f"🟠 ख़तरनाक: शायद {t} स्कैम। कारण देखें",
                  2: "🟡 इस चैट में संदिग्ध संदेश हैं। कारण देखें"},
           "mr": {4: f"🔴 स्कॅम सुरू आहे: बहुधा {t} स्कॅम. मदतीसाठी टॅप करा", 3: f"🟠 धोकादायक: बहुधा {t} स्कॅम. कारण पहा",
                  2: "🟡 या चॅटमध्ये संशयास्पद संदेश आहेत. कारण पहा"}}
    return txt.get(lang, txt["en"])[lvl]


def sos_report(messages: list[dict], lang: str = "en", threshold: float = 0.5, ctx: dict | None = None, conv: dict | None = None) -> dict:
    ch = assess_chat(messages, threshold, ctx, conv)
    inc = [m for m in messages if m.get("direction") == "in" and m.get("analysis")]
    timeline, seen, flags, facts = [], set(), [], []
    for m in inc:
        a = m["analysis"]
        e = explain_message(a, lang, threshold, ctx)
        if e["level"] >= 2:
            s = stage_of(a)
            if s and s not in seen:
                seen.add(s)
                timeline.append({"stage": s, "name": L("stages", s, lang), "message_id": m["id"], "text": m["text"][:140]})
        for t in e["red_flags"]:
            if t not in [f["text"] for f in flags]:
                flags.append({"text": t, "message_id": m["id"]})
        for t in e["facts"]:
            if t not in facts:
                facts.append(t)
    for kind, txt in context_lines(ctx, lang):
        if kind == "flag" and txt not in [f["text"] for f in flags]:
            flags.insert(0, {"text": txt, "message_id": None})
        elif kind == "fact" and txt not in facts:
            facts.append(txt)
    stype = ch["scam_type"]
    if ch["level"] >= 2:
        what = L("what", stype, lang) if stype in T["what"] else L("what", "generic", lang)
        nxt = T["next_step"].get(lang, T["next_step"]["en"]) if ("demand" not in seen and seen) else None
        actions = ([L("actions_type", stype, lang)] if stype in T["actions_type"] else []) + [x.get(lang, x["en"]) for x in T["actions_common"]]
    else:
        what, nxt = T["safe_chat"].get(lang, T["safe_chat"]["en"]), None
        actions = [x.get(lang, x["en"]) for x in T["actions_common"][:2]]
    R = compose_chat(ch.get("_facts") or chat_facts(messages, ctx), ctx, lang, ch["level"])
    if ch["level"] >= 2:
        flags = [{"text": t, "message_id": None} for t in R["lines"]] + [f for f in flags if f["text"] not in R["lines"]]
        facts = R["facts"] + [f for f in facts if f not in R["facts"]]
        actions = R["actions"] + actions
    else:
        what = R["safe"] or what
        facts = R["facts"] + facts
    return {"level": ch["level"], "label": level_name(ch["level"], lang), "scam_type": stype, "scam_type_name": type_name(stype, lang),
            "what": what, "timeline": timeline, "next_step": nxt, "red_flags": flags[:10], "facts": facts[:6], "actions": actions,
            "flagged": ch["flagged"], "stage": ch["stage"], "banner": banner_text(ch, lang)}


def evidence_pack(chat: dict, ctx: dict | None = None) -> str:
    """Plain-text summary for 1930 / cybercrime.gov.in / Chakshu (created only when the user asks)."""
    lines = ["PrahaarShield evidence summary", f"Chat: {chat['name']}  Number: {chat.get('number') or '-'}"]
    if ctx:
        lines.append(f"Account type (as shown by app): {ctx.get('account_type')}  Contact status: {ctx.get('contact_status') or '-'}")
    lines.append("")
    for m in chat["messages"]:
        a = m.get("analysis")
        if m.get("direction") == "in" and a and message_level(a, ctx=ctx) >= 2:
            lines.append(f"[{m.get('time', '')}] {m['text']}")
            for r in a.get("identifiers", []):
                lines.append(f"    {r['type']}: {r['value']}  ({r['risk']})")
    lines += ["", "Report: call 1930 | https://cybercrime.gov.in | Sanchar Saathi (Chakshu): https://sancharsaathi.gov.in"]
    return "\n".join(lines)
