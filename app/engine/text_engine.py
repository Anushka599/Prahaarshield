"""PrahaarShield text engine (M1): loads the fine-tuned MuRIL multi-task model and analyses one message.

Per message: normalize -> entities/placeholders -> M1 (scam prob, type, 6 pillars, language, 768-d vector)
-> calibration (temperature per head, from the config) -> language gate -> hard rules -> identifier checks
-> risky-word highlights (gradient x input, only for risky messages) -> evidence.
The model is rebuilt from the saved weights (BERT config read from weight shapes): no internet needed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path

from engine.entities import prepare_for_model
from engine.identifiers import check_message

PILLARS = ["P_IDENTITY", "P_SITUATION", "P_STAKES", "P_CRED", "P_RESOURCE", "P_CONTROL"]
SUPPORTED = {"en", "hinglish", "hi_deva", "mr"}
RULES = {
    "cred_ask": re.compile(r"\b(share|send|tell|enter|give|provide|confirm|forward|read out|bata|batao|bataiye|bhej|bhejo|daal|daalo|de do|sanga|pathva)\b"
                           r"[^.\n]{0,40}\b(otp|m?pin|password|cvv|code)\b|\b(otp|m?pin|password|cvv)\b[^.\n]{0,25}\b(share|send|bata|batao|bhej|bhejo|de do|sanga|pathva)\b|"
                           r"(ओटीपी|पिन|कोड)[^।\n]{0,25}(बताइए|बताएं|बताओ|भेजें|भेजो|दीजिए|सांगा|पाठवा)", re.I),
    "apk": re.compile(r"\.apk\b|\.exe\b|anydesk|teamviewer|quick ?support|rustdesk|screen ?share|install[^.\n]{0,25}\bapp\b|\bapp\b[^.\n]{0,15}install", re.I),
    "upi_pin_collect": re.compile(r"collect request|approve[^.\n]{0,30}(pin|upi|request)|pin (daal|dalo|enter)|enter[^.\n]{0,15}upi pin[^.\n]{0,30}(receive|get|refund)", re.I),
    "gift_codes": re.compile(r"gift ?cards?|vouchers?[^.\n]{0,30}codes?|scratch codes?|google play (card|code)", re.I),
    "safe_account": re.compile(r"(safe|secure|verification|rbi|government|sarkari|suraksha)[^.\n]{0,15}(account|a/c|khate|खाते|खाता)|"
                               r"सुरक्षित खात|सरकारी खात", re.I),
    "wa_code": re.compile(r"(code|otp|कोड).{0,40}(galti|by mistake|mistake|चुकून|गलती)|(galti|mistake|चुकून|गलती).{0,40}(code|otp|कोड)|"
                          r"(forward|share|bhej|pathav|पाठव|भेज)\w*\s+(kar\s+|karo\s+|me\s+)?(the\s+|that\s+|wo\s+|to\s+)?(6.?digit\s+)?(whatsapp\s+)?(verification\s+)?code|6.?digit\s+code|6\s?अंकी", re.I),
}


RULE_EXCLUDE = {  # genuine wording that looks like a rule hit
    "upi_pin_collect": re.compile(r"mandate|autopay|auto-pay|\bipo\b|asba|e-?mandate", re.I),
}
# "Your OTP is 4829. Do NOT share it" is a warning, not an ask -> cred_ask is dropped, unless the message ALSO asks for the code
_NEG_SHARE = re.compile(r"\b(never|do not|don'?t|dont)\s+(share|disclose|tell)|share\s+na\s+kar|mat\s+(share|bataye|batayen|batana\s+kisi)|साझा\s+न|शेयर\s+न|शेअर\s+करू\s+नका|सांगू\s+नका|कोणालाही\s+सांगू|किसी\s+(को|से)\s+(न|मत)", re.I)
_ASK_SHARE = re.compile(r"\b(bata\s*do|batao|bhejo|bhej\s*do|send\s+(it|me|kar|karo|the)|share\s+(it\s+)?(with\s+me|here|kar|karo)|tell\s+me|sanga|sang\s*na|de\s*do)\b|बताओ|बता\s*दो|भेजो|भेज\s*दो|सांगा|पाठवा", re.I)


def _rule_excluded(name: str, text: str) -> bool:
    if name in RULE_EXCLUDE and RULE_EXCLUDE[name].search(text):
        return True
    return name == "cred_ask" and bool(_NEG_SHARE.search(text)) and not _ASK_SHARE.search(text)


def _reliable(lang: str, text_model: str) -> bool:
    words = len(re.findall(r"[^\W\d_]{2,}", re.sub(r"<[A-Z_]+>", " ", text_model)))
    return lang in SUPPORTED and words >= 3


def find_model_dir() -> Path:
    app_dir = Path(__file__).resolve().parents[1]
    cands = [os.environ.get("PRAHAAR_MODEL_DIR"), app_dir.parent / "models", app_dir / "models", r"C:\PRahaarshield_Miniproject\models"]
    for c in cands:
        if c and (Path(c) / "muril_multitask_config.json").exists():
            return Path(c)
    raise FileNotFoundError("muril_multitask_config.json not found. Looked in:\n  " + "\n  ".join(str(c) for c in cands if c)
                            + "\nPut the model files in one of these folders (or set PRAHAAR_MODEL_DIR).")


def build_result(text, norm, ent, p, tprobs, pprobs, lprobs, TYPES, LANGS, threshold):
    ti = max(range(len(TYPES)), key=lambda i: tprobs[i])
    li = max(range(len(LANGS)), key=lambda i: lprobs[i])
    lang = LANGS[li]
    dev = len(re.findall(r"[\u0900-\u097F]", norm.clean)); lat = len(re.findall(r"[A-Za-z]", norm.clean))
    if dev >= 3 and dev > lat and lang not in ("hi_deva", "mr"):     # Devanagari text: the script decides, the head picks Hindi vs Marathi
        cand = [(lprobs[LANGS.index(l)], l) for l in ("hi_deva", "mr") if l in LANGS]
        lang = max(cand)[1] if cand else "hi_deva"
    elif lang == "hi_deva" and dev == 0:
        lang = "hinglish"                                            # Roman letters can't be Devanagari Hindi
    rules = [name for name, rx in RULES.items() if rx.search(norm.clean) and not _rule_excluded(name, norm.clean)]
    return {
        "p_scam": round(float(p), 4), "is_scam": float(p) >= threshold, "scam_type": TYPES[ti], "type_conf": round(float(tprobs[ti]), 3),
        "pillars": {k: round(float(v), 3) for k, v in zip(PILLARS, pprobs)}, "language": lang,
        "text_reliable": _reliable(lang, ent.text_model), "rules": rules, "obfuscation_detected": bool(norm.obfuscation_detected),
        "tricks": norm.tricks, "entities": {k: len(v) for k, v in ent.found.items()},
        "identifiers": check_message(ent.found, norm.clean), "clean_text": norm.clean, "highlights": [],
    }


class TextEngine:
    def __init__(self, model_dir: str | Path):
        import torch
        import torch.nn as nn
        from transformers import AutoTokenizer, BertConfig, BertModel

        model_dir = Path(model_dir)
        self.torch = torch
        cfg = json.load(open(model_dir / "muril_multitask_config.json", encoding="utf-8"))
        self.TYPES, self.LANGS = cfg["TYPES"], cfg["LANGS"]
        self.threshold = float(cfg.get("threshold", 0.5))
        self.temps = {"scam": 1.0, "type": 1.0, "pillar": 1.0, **cfg.get("temperatures", {})}
        self.max_len = int(cfg["CFG"].get("max_len", 256))
        self.tok = AutoTokenizer.from_pretrained(str(model_dir / "muril_multitask_tokenizer"))
        sd = torch.load(model_dir / "muril_multitask.pt", map_location="cpu", weights_only=True)
        W = sd["enc.embeddings.word_embeddings.weight"]
        n_layers = 1 + max(int(k.split(".")[3]) for k in sd if k.startswith("enc.encoder.layer."))
        bc = BertConfig(vocab_size=W.shape[0], hidden_size=W.shape[1], num_hidden_layers=n_layers, num_attention_heads=W.shape[1] // 64,
                        intermediate_size=sd["enc.encoder.layer.0.intermediate.dense.weight"].shape[0],
                        max_position_embeddings=sd["enc.embeddings.position_embeddings.weight"].shape[0],
                        type_vocab_size=sd["enc.embeddings.token_type_embeddings.weight"].shape[0])
        pooler = any(k.startswith("enc.pooler") for k in sd)
        n_types, n_langs = len(self.TYPES), len(self.LANGS)

        def make_bert():
            try:
                return BertModel(bc, add_pooling_layer=pooler)
            except TypeError:
                return BertModel(bc)

        class PrahaarModel(nn.Module):
            def __init__(self):
                super().__init__()
                self.enc = make_bert()
                h = bc.hidden_size
                self.drop = nn.Dropout(0.1)
                self.scam, self.stype = nn.Linear(h, 2), nn.Linear(h, n_types)
                self.pil, self.lang = nn.Linear(h, len(PILLARS)), nn.Linear(h, n_langs)

            def pooled(self, mask, ids=None, embeds=None):
                hs = self.enc(input_ids=ids, inputs_embeds=embeds, attention_mask=mask).last_hidden_state
                m = mask.unsqueeze(-1).float()
                return (hs * m).sum(1) / m.sum(1).clamp(min=1)

            def forward(self, ids, mask):
                x = self.pooled(mask, ids=ids)
                return self.scam(x), self.stype(x), self.pil(x), self.lang(x), x

        self.model = PrahaarModel()
        missing, _ = self.model.load_state_dict(sd, strict=False)
        missing = [k for k in missing if not k.endswith("position_ids")]
        if missing:
            raise RuntimeError(f"model weights missing keys: {missing[:5]}")
        self.model.eval()
        for prm in self.model.parameters():          # inference only: gradients are needed for highlights' inputs, not weights
            prm.requires_grad_(False)
        torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))

    def _forward(self, text_model: str):
        torch = self.torch
        enc = self.tok([text_model], truncation=True, max_length=self.max_len, return_tensors="pt")
        with torch.no_grad():
            o_s, o_t, o_p, o_l, vec = self.model(enc["input_ids"], enc["attention_mask"])
        raw_p = float(torch.softmax(o_s, -1)[0, 1]); raw_pil = torch.sigmoid(o_p)[0].tolist(); raw_t = torch.softmax(o_t, -1)[0].tolist()
        cal = (float(torch.softmax(o_s / self.temps["scam"], -1)[0, 1]), torch.softmax(o_t / self.temps["type"], -1)[0].tolist(),
               torch.sigmoid(o_p / self.temps["pillar"])[0].tolist(), torch.softmax(o_l, -1)[0].tolist())
        return cal, {"vec": vec[0].tolist(), "raw": [raw_p] + raw_pil + raw_t}

    def _predict(self, text_model: str):
        if len(self.tok(text_model)["input_ids"]) <= self.max_len:
            return self._forward(text_model)
        words, best = text_model.split(), None
        for start in range(0, len(words), 120):
            out = self._forward(" ".join(words[start:start + 160]))
            if best is None or out[0][0] > best[0][0]:
                best = out
            if start + 160 >= len(words):
                break
        return best

    def highlights(self, text_model: str, top_k: int = 4) -> list[str]:
        """Words that pushed the scam score up most (gradient x input on the word embeddings)."""
        torch = self.torch
        enc = self.tok([text_model], truncation=True, max_length=self.max_len, return_tensors="pt", return_offsets_mapping=True)
        offsets = enc.pop("offset_mapping")[0].tolist()
        word_ids = enc.word_ids(0)
        emb = self.model.enc.embeddings.word_embeddings(enc["input_ids"]).detach().requires_grad_(True)
        x = self.model.pooled(enc["attention_mask"], embeds=emb)
        logit = self.model.scam(x)[0]
        (logit[1] - logit[0]).backward()
        attr = (emb.grad[0] * emb[0]).sum(-1).tolist()
        words = {}
        for i, w in enumerate(word_ids):
            if w is None:
                continue
            s, e = offsets[i]
            cur = words.setdefault(w, [0.0, s, e])
            cur[0] += attr[i]; cur[1] = min(cur[1], s); cur[2] = max(cur[2], e)
        STOP = {"se", "at", "or", "to", "in", "of", "on", "is", "the", "and", "an", "ka", "ki", "ke", "ko", "hai", "hi", "me", "mein", "pe", "par", "ho",
                "hoga", "aur", "ya", "ye", "wo", "na", "bhi", "tum", "aap", "mi", "tu", "la", "for", "you", "your", "this", "that", "with",
                "चा", "ची", "के", "की", "का", "है", "में", "से", "को", "और", "ने", "पर", "या", "तो", "हो", "आहे", "व", "ना", "मग"}
        cands = [(sc, s, e) for sc, s, e in words.values() if sc > 0 and not re.fullmatch(r"[<>\W_]*|[A-Z_]+", text_model[s:e])
                 and text_model[s:e].strip().lower() not in STOP and (e - s >= 3 or re.search(r"[\u0900-\u097F]", text_model[s:e]))]
        if not cands:
            return []
        mx = max(c[0] for c in cands)
        keep = sorted([c for c in cands if c[0] >= 0.25 * mx], key=lambda c: -c[0])[:top_k]
        keep.sort(key=lambda c: c[1])
        phrases, cur = [], None
        for sc, s, e in keep:                       # merge neighbouring words into short phrases
            if cur and s - cur[1] <= 2:
                cur = (cur[0], e)
            else:
                if cur: phrases.append(text_model[cur[0]:cur[1]])
                cur = (s, e)
        if cur: phrases.append(text_model[cur[0]:cur[1]])
        return [p.strip() for p in phrases if len(p.strip()) >= 2]

    def analyze_full(self, text: str, with_highlights: bool = True):
        norm, ent = prepare_for_model(text)
        (p, tprobs, pprobs, lprobs), feats = self._predict(ent.text_model)
        a = build_result(text, norm, ent, p, tprobs, pprobs, lprobs, self.TYPES, self.LANGS, self.threshold)
        if with_highlights and p >= self.threshold:
            try:
                a["highlights"] = self.highlights(ent.text_model)
            except Exception as ex:                  # explanations must never break detection
                a["highlights_error"] = str(ex)[:80]
        return a, feats

    def analyze(self, text: str) -> dict:
        return self.analyze_full(text)[0]

    def features(self, text: str) -> dict:
        """Vector + raw scores only (used for the user's own messages, which are never alerted on)."""
        norm, ent = prepare_for_model(text)
        return self._predict(ent.text_model)[1]


class MockEngine:
    """TEST ONLY (set PRAHAAR_MOCK=1): fake scores from simple cues, to test the app without the model."""
    TYPES = ["boss_impersonation", "digital_arrest", "investment_group", "job_task", "kyc_bank", "loan_app"]
    LANGS = ["en", "hi_deva", "hinglish", "mr", "other"]
    threshold = 0.5
    CUES = {"police": 1, "arrest": 2, "otp": 2, "kyc": 1, "transfer": 1, "deposit": 1, "fee": 1, "urgent": 1, "guaranteed": 1, "loan": 1,
            "task": 1, "gift card": 2, "<url>": 1, "pin": 1, "cbi": 2, "profit": 1, "warrant": 2, "safe account": 2}

    def _feats(self, text, p, pp):
        h = hashlib.sha256(text.encode()).digest()
        return {"vec": [((h[i % 32] / 255.0) - 0.5) for i in range(768)], "raw": [p] + pp + [1 / 6] * 6}

    def analyze_full(self, text: str, with_highlights: bool = True):
        norm, ent = prepare_for_model(text)
        t = norm.clean.lower() + " " + ent.text_model.lower()
        s = sum(v for k, v in self.CUES.items() if k in t)
        p = min(0.97, 0.05 + 0.18 * s)
        tp = [0.1] * 6
        for i, kw in enumerate(["boss", "arrest", "profit", "task", "kyc", "loan"]):
            if kw in t:
                tp[i] = 0.9
        z = sum(tp); tp = [x / z for x in tp]
        pp = [min(0.9, p + 0.1 if k in t else p - 0.2) for k in ["police", "case", "arrest", "otp", "transfer", "mat batana"]]
        lp = [0.7, 0.05, 0.2, 0.03, 0.02]
        a = build_result(text, norm, ent, p, tp, pp, lp, self.TYPES, self.LANGS, self.threshold)
        if with_highlights and p >= self.threshold:
            a["highlights"] = [k for k in self.CUES if k in norm.clean.lower()][:4]
        return a, self._feats(text, p, pp)

    def analyze(self, text: str) -> dict:
        return self.analyze_full(text)[0]

    def features(self, text: str) -> dict:
        return self.analyze_full(text, False)[1]


def load_engine(model_dir: str | Path | None = None):
    if os.environ.get("PRAHAAR_MOCK") == "1":
        print("[engine] MOCK engine (testing only)")
        return MockEngine()
    model_dir = Path(model_dir) if model_dir and (Path(model_dir) / "muril_multitask_config.json").exists() else find_model_dir()
    tok_dir = model_dir / "muril_multitask_tokenizer"
    if not (tok_dir / "tokenizer_config.json").exists():
        raise FileNotFoundError(f"{tok_dir} must be a folder containing tokenizer_config.json "
                                "(unzip the Google Drive download and rename the folder exactly).")
    print(f"[engine] loading MuRIL model from {model_dir} ...")
    eng = TextEngine(model_dir)
    print(f"[engine] model ready (threshold {eng.threshold}, temperatures {eng.temps})")
    return eng
