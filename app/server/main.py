"""PrahaarShield server v3 (FastAPI).  Run from the app folder:
    python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
Testing UI : http://localhost:8000/sim          (both sides)      ?view=user (phone)   ?view=scam (laptop)
All AI runs inside this process on the laptop; nothing is sent to any cloud service.
"""
from __future__ import annotations

import asyncio
import copy
import csv
import io
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from brain.brain import (LEVELS, assess_chat, banner_text, evidence_pack, explain_message, level_name, message_level, sos_report)
from engine.conversation import load_conv
from engine.identifiers import REGISTRY_LABEL, check_phone
from engine.text_engine import find_model_dir, load_engine

APP_DIR = Path(__file__).resolve().parents[1]
DEMO = json.load(open(APP_DIR / "demo" / "demo_chats.json", encoding="utf-8"))
engine = load_engine(os.environ.get("PRAHAAR_MODEL_DIR"))
try:
    _mdir = None if os.environ.get("PRAHAAR_MOCK") == "1" else find_model_dir()
except FileNotFoundError:
    _mdir = None
conv_engine = load_conv(_mdir)
THRESHOLD = float(getattr(engine, "threshold", 0.5))
app = FastAPI(title="PrahaarShield")
STATE = {"chats": {}, "settings": {"live_guard": True, "protect_new": True, "lang": "en"}}
SOCKETS: set[WebSocket] = set()
SIM_ID = "sim"
FEEDBACK = APP_DIR / "feedback" / "feedback_log.jsonl"
DEFAULT_SETUP = {"lang": None, "account_type": "general", "name": "Unknown Person", "chat_type": "single",
                 "contacts_permission": False, "contact_status": None, "number": "+91 7XXXX XXXXX"}


def now() -> str:
    return time.strftime("%H:%M")


async def broadcast(payload: dict):
    dead = []
    for ws in SOCKETS:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        SOCKETS.discard(ws)


# ------------------------------------------------------------------ chat processing
def ctx_of(c: dict) -> dict | None:
    s = c.get("setup")
    if not s:
        return None
    ctx = dict(s)
    joined = " ".join(m["text"] for m in c["messages"] if m["direction"] == "in")
    ctx["sender_check"] = check_phone(s.get("number") or "", joined, is_sender=True,
                                      contact_status=s.get("contact_status") if s.get("contacts_permission") else None) if s.get("number") else None
    return ctx


def process_msg(m: dict):
    if m.get("kind", "text") != "text":
        return
    if m["direction"] == "in" and m.get("analysis") is None:
        m["analysis"], m["feats"] = engine.analyze_full(m["text"])
    elif m["direction"] == "out" and m.get("feats") is None:
        m["feats"] = engine.features(m["text"])


def conv_of(c: dict) -> dict | None:
    if conv_engine is None:
        return None
    items = [{"vec": m["feats"]["vec"], "raw": m["feats"]["raw"], "speaker": "them" if m["direction"] == "in" else "me"}
             for m in c["messages"] if m.get("feats")]
    return conv_engine.predict(items)


def check_chat(c: dict):
    for m in c["messages"]:
        process_msg(m)
    c["conv"] = conv_of(c)
    c["assessment"] = assess_chat(c["messages"], THRESHOLD, ctx_of(c), c["conv"])


def msg_view(m: dict, ctx: dict | None, lang: str) -> dict:
    v = {k: m.get(k) for k in ("id", "direction", "text", "time", "kind", "content", "file_name")}
    a = m.get("analysis")
    if a:
        v["level"] = message_level(a, THRESHOLD, ctx)
        v["explain"] = explain_message(a, lang, THRESHOLD, ctx)
        v["debug"] = {"p_scam": a["p_scam"], "scam_type": a["scam_type"], "type_conf": a["type_conf"], "language": a["language"],
                      "reliable": a["text_reliable"], "pillars": {k: x for k, x in a["pillars"].items() if x >= 0.5},
                      "rules": a["rules"], "tricks": a["tricks"], "highlights": a.get("highlights", []),
                      "identifiers": [{"type": i["type"], "value": i["value"], "risk": i["risk"]} for i in a.get("identifiers", [])]}
    return v


def chat_summary(c: dict, lang: str = "en") -> dict:
    a = c["assessment"]
    last = c["messages"][-1] if c["messages"] else None
    return {"id": c["id"], "name": c["name"], "number": c.get("number"), "is_group": c.get("is_group", False), "saved": c.get("saved", True),
            "last": (last["text"][:60] if last else ""), "time": (last["time"] if last else ""), "level": a["level"],
            "label": level_name(a["level"], lang), "checked": a["checked"], "scam_type": a["scam_type"], "stage": a.get("stage"),
            "reasons": a.get("reasons", []), "banner": banner_text(a, lang), "muted": c.get("muted", False),
            "conv": c.get("conv")}


def empty_assessment():
    return {"level": 0, "label": LEVELS[0], "checked": False, "scam_type": None, "flagged": [], "stage": None, "reasons": []}


def reset_demo():
    STATE["chats"] = {}
    for c in copy.deepcopy(DEMO["chats"]):
        for i, m in enumerate(c["messages"]):
            m["id"] = f"{c['id']}-{i}"
            m.setdefault("time", "10:%02d" % (i + 1))
            m["analysis"] = None
        c["assessment"] = empty_assessment()
        STATE["chats"][c["id"]] = c


reset_demo()


# ------------------------------------------------------------------ pages
@app.get("/")
def page_index():
    return FileResponse(APP_DIR / "frontend" / "index.html")


@app.get("/sim")
def page_sim():
    return FileResponse(APP_DIR / "frontend" / "sim.html")


@app.get("/sender")
def page_sender():
    return FileResponse(APP_DIR / "frontend" / "sender.html")


@app.get("/api/info")
def api_info():
    return {"engine": type(engine).__name__, "threshold": THRESHOLD, "temperatures": getattr(engine, "temps", None),
            "conversation_model": type(conv_engine).__name__ if conv_engine else "rules (no conv_model.pt)", "registry": REGISTRY_LABEL}


# ------------------------------------------------------------------ two-sided test chat (/sim)
def sim_chat() -> dict:
    if SIM_ID not in STATE["chats"]:
        STATE["chats"][SIM_ID] = {"id": SIM_ID, "name": DEFAULT_SETUP["name"], "number": DEFAULT_SETUP["number"], "saved": False,
                                  "is_group": False, "messages": [], "setup": dict(DEFAULT_SETUP), "assessment": empty_assessment()}
    return STATE["chats"][SIM_ID]


class Setup(BaseModel):
    lang: str | None = None
    account_type: str | None = None
    name: str | None = None
    chat_type: str | None = None
    contacts_permission: bool | None = None
    contact_status: str | None = None
    number: str | None = None


@app.get("/api/sim/session")
def api_sim_session():
    c = sim_chat()
    lang = c["setup"].get("lang") or "en"
    return {"setup": c["setup"], "chat": chat_summary(c, lang), "messages": [msg_view(m, ctx_of(c), lang) for m in c["messages"]]}


@app.post("/api/sim/setup")
async def api_sim_setup(s: Setup):
    c = sim_chat()
    for k, v in s.model_dump().items():
        if v is not None:
            c["setup"][k] = v.strip() if isinstance(v, str) else v
    if not c["setup"].get("contacts_permission"):
        c["setup"]["contact_status"] = None
    c["name"], c["number"] = c["setup"]["name"], c["setup"]["number"]
    c["is_group"] = c["setup"]["chat_type"] == "group"
    c["saved"] = c["setup"].get("contact_status") == "safe"
    if c["messages"]:
        await asyncio.to_thread(check_chat, c)
    else:
        c["assessment"] = assess_chat([], THRESHOLD, ctx_of(c), None)
    await broadcast({"type": "sim", "event": "setup"})
    return api_sim_session()


class SimMsg(BaseModel):
    sender: str                 # "scam" = other person (analysed) | "user" = the user (never alerted on)
    text: str = ""
    kind: str = "text"          # text | image | doc
    content: str | None = None  # data URL for images (shown on both screens)
    file_name: str | None = None


@app.post("/api/sim/send")
async def api_sim_send(m: SimMsg):
    c = sim_chat()
    if m.kind == "text" and not m.text.strip():
        raise HTTPException(400, "empty message")
    lang = c["setup"].get("lang") or "en"
    direction = "in" if m.sender == "scam" else "out"
    msg = {"id": f"{SIM_ID}-{len(c['messages'])}-{int(time.time()*1000) % 100000}", "direction": direction, "kind": m.kind,
           "text": m.text if m.kind == "text" else f"[{m.kind}] {m.file_name or m.text}".strip(), "time": now(),
           "analysis": None, "content": m.content if m.kind == "image" else None, "file_name": m.file_name}
    c["messages"].append(msg)
    before = c["assessment"]["level"]
    await asyncio.to_thread(check_chat, c)
    after = c["assessment"]["level"]
    alert = None
    if direction == "in" and msg.get("analysis"):
        lvl = message_level(msg["analysis"], THRESHOLD, ctx_of(c))
        if c.get("muted") and lvl < 3 and after < 4:
            pass
        elif after >= 3 and (after > before or lvl >= 3):
            c["muted"] = False
            alert = {"level": after, "label": level_name(after, lang), "text": msg["text"][:90], "banner": banner_text(c["assessment"], lang)}
    out = {"message": msg_view(msg, ctx_of(c), lang), "chat": chat_summary(c, lang), "alert": alert}
    await broadcast({"type": "sim", "event": "message", **out})
    return out


@app.post("/api/sim/reset")
async def api_sim_reset(new_session: bool = False):
    c = sim_chat()
    setup = dict(DEFAULT_SETUP) if new_session else c["setup"]
    STATE["chats"].pop(SIM_ID, None)
    c = sim_chat()
    c["setup"] = setup
    c["name"], c["number"] = setup["name"], setup["number"]
    c["assessment"] = assess_chat([], THRESHOLD, ctx_of(c), None)
    await broadcast({"type": "sim", "event": "reset", "new_session": new_session})
    return {"ok": True}


@app.post("/api/sim/not_scam")
async def api_sim_not_scam():
    sim_chat()["muted"] = True
    await broadcast({"type": "sim", "event": "setup"})
    return {"ok": True}


# ------------------------------------------------------------------ chats (SOS / evidence work for /sim and the demo chats)
@app.post("/api/chat/{cid}/sos")
async def api_sos(cid: str, lang: str | None = None):
    c = STATE["chats"].get(cid) or _404()
    await asyncio.to_thread(check_chat, c)
    lang = lang or (c.get("setup") or {}).get("lang") or "en"
    return sos_report(c["messages"], lang, THRESHOLD, ctx_of(c), c.get("conv"))


@app.get("/api/chat/{cid}/evidence", response_class=PlainTextResponse)
def api_evidence(cid: str):
    c = STATE["chats"].get(cid) or _404()
    return evidence_pack(c, ctx_of(c))


def _404():
    raise HTTPException(404, "chat not found")


@app.get("/api/state")
def api_state():
    lang = STATE["settings"]["lang"]
    chats = [c for c in STATE["chats"].values() if c["id"] != SIM_ID]
    chats.sort(key=lambda c: c["messages"][-1]["time"] if c["messages"] else "", reverse=True)
    return {"chats": [chat_summary(c, lang) for c in chats], "settings": STATE["settings"]}


@app.get("/api/chat/{cid}")
def api_chat(cid: str, lang: str = "en"):
    c = STATE["chats"].get(cid) or _404()
    return {"chat": chat_summary(c, lang), "messages": [msg_view(m, ctx_of(c), lang) for m in c["messages"]]}


@app.post("/api/chat/{cid}/check")
async def api_check(cid: str, lang: str = "en"):
    c = STATE["chats"].get(cid) or _404()
    await asyncio.to_thread(check_chat, c)
    await broadcast({"type": "update", "chat_id": cid})
    return api_chat(cid, lang)


@app.post("/api/check_all")
async def api_check_all():
    for c in STATE["chats"].values():
        if c["id"] != SIM_ID:
            await asyncio.to_thread(check_chat, c)
    await broadcast({"type": "update", "chat_id": None})
    lang = STATE["settings"]["lang"]
    flagged = [chat_summary(c, lang) for c in STATE["chats"].values() if c["id"] != SIM_ID and c["assessment"]["level"] >= 2]
    return {"checked": len(STATE["chats"]) - (1 if SIM_ID in STATE["chats"] else 0), "flagged": len(flagged),
            "critical": sum(1 for f in flagged if f["level"] >= 4), "chats": flagged}


class Msg(BaseModel):
    chat_id: str | None = None
    name: str | None = None
    number: str | None = None
    direction: str = "in"
    text: str


@app.post("/api/message")
async def api_message(m: Msg):
    cid = m.chat_id if m.chat_id in STATE["chats"] else (m.chat_id or "new-" + str(int(time.time())))
    if cid not in STATE["chats"]:
        STATE["chats"][cid] = {"id": cid, "name": m.name or m.number or "Unknown", "number": m.number, "saved": False, "is_group": False,
                               "messages": [], "assessment": empty_assessment()}
    c = STATE["chats"][cid]
    c["messages"].append({"id": f"{cid}-{len(c['messages'])}", "direction": m.direction, "text": m.text, "time": now(), "analysis": None})
    before = c["assessment"]["level"]
    if STATE["settings"]["live_guard"] or not c.get("saved", True):
        await asyncio.to_thread(check_chat, c)
    after = c["assessment"]["level"]
    alert = {"chat_id": cid, "level": after, "label": LEVELS[after], "text": m.text[:80]} if after >= 3 and after > before else None
    await broadcast({"type": "update", "chat_id": cid, "alert": alert})
    return {"chat_id": cid, "alert": alert}


@app.post("/api/chat/{cid}/not_scam")
async def api_not_scam(cid: str):
    (STATE["chats"].get(cid) or _404())["muted"] = True
    await broadcast({"type": "update", "chat_id": cid})
    return {"ok": True}


class Settings(BaseModel):
    live_guard: bool | None = None
    protect_new: bool | None = None
    lang: str | None = None


@app.post("/api/settings")
async def api_settings(s: Settings):
    for k, v in s.model_dump().items():
        if v is not None:
            STATE["settings"][k] = v
    await broadcast({"type": "settings"})
    return STATE["settings"]


@app.post("/api/reset_demo")
async def api_reset():
    reset_demo()
    await broadcast({"type": "update", "chat_id": None})
    return {"ok": True}


@app.get("/api/scripts")
def api_scripts():
    return DEMO.get("scripts", [])


@app.post("/api/analyze")
def api_analyze(m: Msg):
    a = engine.analyze(m.text)
    return {"analysis": a, "level": message_level(a, THRESHOLD), "explain": explain_message(a, "en", THRESHOLD)}


# ------------------------------------------------------------------ feedback (✓ / ✗ from the testing UI)
class Feedback(BaseModel):
    message_id: str
    expected: str               # "scam" | "benign"
    note: str = ""


@app.post("/api/feedback")
def api_feedback(f: Feedback):
    c = sim_chat()
    m = next((x for x in c["messages"] if x["id"] == f.message_id), None)
    if not m or not m.get("analysis"):
        raise HTTPException(404, "message not found or not analysed")
    a, ctx = m["analysis"], ctx_of(c)
    FEEDBACK.parent.mkdir(exist_ok=True)
    row = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "text": m["text"], "expected": f.expected, "model_p_scam": a["p_scam"],
           "model_level": message_level(a, THRESHOLD, ctx), "model_type": a["scam_type"],
           "model_pillars": [k for k, v in a["pillars"].items() if v >= 0.5], "rules": a["rules"], "language": a["language"], "note": f.note,
           "chat_level": c["assessment"]["level"], "conv": c.get("conv"), "setup": {k: v for k, v in c["setup"].items() if k != "lang"},
           "context": [x["text"] for x in c["messages"] if x["direction"] == "in" and x.get("kind", "text") == "text"][-4:-1]}
    with open(FEEDBACK, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True, "logged": sum(1 for _ in open(FEEDBACK, encoding="utf-8"))}


@app.get("/api/feedback/export", response_class=PlainTextResponse)
def api_feedback_export():
    if not FEEDBACK.exists():
        return "no feedback yet"
    rows = [json.loads(l) for l in open(FEEDBACK, encoding="utf-8") if l.strip()]
    buf = io.StringIO(); w = csv.writer(buf)
    cols = ["time", "text", "expected", "model_p_scam", "model_level", "model_type", "model_pillars", "rules", "language", "note", "chat_level"]
    w.writerow(cols)
    for r in rows:
        w.writerow([("|".join(r[k]) if isinstance(r.get(k), list) else r.get(k)) for k in cols])
    return PlainTextResponse(buf.getvalue(), headers={"Content-Disposition": "attachment; filename=prahaar_feedback.csv"})


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    SOCKETS.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        SOCKETS.discard(ws)
