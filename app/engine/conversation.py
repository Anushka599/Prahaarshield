"""PrahaarShield conversation engine (M7).

Reads the last N messages of a chat (both sides) and answers, for the chat SO FAR:
  - is this a scam conversation?   (chat_is_scam)
  - which stage has it reached?    (none / approach / pressure / demand)
  - which scam type?
Features per message (feat = "scores13"): M1's raw scam probability + 6 pillar probabilities + 6 scam-type probabilities, plus speaker (them / me).
Only low-dimensional scores are used (not the 768-d vector) so the model generalises and can be trained on cross-fitted (out-of-fold) scores.
The chat probability is re-scaled so that 0.5 means 'alert' (threshold tuned on validation chats and stored in conv_config.json).
Old v1 models (feat = "vec775") still load. If no model file exists, the Brain falls back to rule-based stage tracking.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

STAGES = ["none", "approach", "pressure", "demand"]
FEAT_DIM = 768 + 7          # v1
MAX_MSGS = 8


def rescale(p: float, th: float) -> float:
    """Monotone re-scaling so that probability == th maps to 0.5."""
    lg = lambda x: math.log(min(max(x, 1e-6), 1 - 1e-6) / (1 - min(max(x, 1e-6), 1 - 1e-6)))
    return 1.0 / (1.0 + math.exp(-(lg(p) - lg(th))))


def build_conv_model(n_types: int, d: int = 256, layers: int = 2, heads: int = 4, max_msgs: int = MAX_MSGS, feat_dim: int = FEAT_DIM):
    import torch
    import torch.nn as nn

    class ConvModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.inp = nn.Sequential(nn.LayerNorm(feat_dim), nn.Linear(feat_dim, d))
            self.spk = nn.Embedding(2, d)
            self.pos = nn.Embedding(max_msgs, d)
            layer = nn.TransformerEncoderLayer(d, heads, 2 * d, dropout=0.1, batch_first=True)
            self.enc = nn.TransformerEncoder(layer, layers)
            self.scam, self.stage, self.stype = nn.Linear(d, 2), nn.Linear(d, len(STAGES)), nn.Linear(d, n_types)

        def forward(self, x, spk, pad):                # x [B,N,F]  spk [B,N] long  pad [B,N] bool (True = padding)
            n = x.shape[1]
            pos = torch.arange(n, device=x.device).unsqueeze(0).expand(x.shape[0], n)
            h = self.inp(x) + self.spk(spk) + self.pos(pos)
            causal = torch.triu(torch.ones(n, n, dtype=torch.bool, device=x.device), 1)
            h = self.enc(h, mask=causal, src_key_padding_mask=pad)
            return self.scam(h), self.stage(h), self.stype(h)

    return ConvModel()


class ConvEngine:
    def __init__(self, model_dir: Path):
        import torch
        cfg = json.load(open(model_dir / "conv_config.json", encoding="utf-8"))
        self.torch, self.TYPES, self.cfg = torch, cfg["TYPES"], cfg
        self.max_msgs = cfg.get("max_msgs", MAX_MSGS)
        self.feat = "scores13" if str(cfg.get("feat", "")).startswith("scores13") else "vec775"
        self.th = cfg.get("threshold") if self.feat == "scores13" else None
        fd = 13 if self.feat == "scores13" else FEAT_DIM
        self.model = build_conv_model(len(self.TYPES), cfg.get("d", 256), cfg.get("layers", 2), cfg.get("heads", 4), self.max_msgs, fd)
        self.model.load_state_dict(torch.load(model_dir / "conv_model.pt", map_location="cpu", weights_only=True))
        self.model.eval()

    def predict(self, items: list[dict]) -> dict | None:
        """items: [{'vec': [...768], 'raw': [...13], 'speaker': 'them'|'me'}] oldest -> newest."""
        items = [i for i in items if i.get("raw")][-self.max_msgs:]
        if not items or not any(i["speaker"] == "them" for i in items):
            return None
        torch = self.torch
        if self.feat == "scores13":
            if len(items[0]["raw"]) < 13:
                return None
            rows = [i["raw"][:13] for i in items]
        else:
            rows = [i["vec"] + i["raw"][:7] for i in items]
        x = torch.tensor([rows], dtype=torch.float)
        spk = torch.tensor([[0 if i["speaker"] == "them" else 1 for i in items]])
        pad = torch.zeros(1, len(items), dtype=torch.bool)
        with torch.no_grad():
            s, st, ty = self.model(x, spk, pad)
        last_them = max(k for k, i in enumerate(items) if i["speaker"] == "them")
        p = float(torch.softmax(s[0, -1], -1)[1])
        if self.th:
            p = rescale(p, self.th)
        stage = STAGES[int(st[0, last_them].argmax())]
        return {"p_scam": round(p, 4), "stage": stage, "scam_type": self.TYPES[int(ty[0, -1].argmax())], "n_msgs": len(items)}


class MockConv:
    """TEST ONLY: chat score = max recent raw scam score; stage from the last risky message's pillars."""
    def predict(self, items):
        them = [i for i in items if i["speaker"] == "them"][-MAX_MSGS:]
        if not them:
            return None
        p = max(i["raw"][0] for i in them)
        last = max(them, key=lambda i: i["raw"][0])["raw"][1:]
        stage = "demand" if max(last[3], last[4]) >= .5 else "pressure" if max(last[2], last[5]) >= .5 else "approach" if max(last[0], last[1]) >= .5 else "none"
        return {"p_scam": round(p, 4), "stage": stage, "scam_type": None, "n_msgs": len(them)}


def load_conv(model_dir: Path | None):
    if os.environ.get("PRAHAAR_NO_CONV") == "1":
        print("[conv] PRAHAAR_NO_CONV=1 -> conversation model switched off (rule-based stage tracking only)")
        return None
    if os.environ.get("PRAHAAR_MOCK") == "1":
        return MockConv()
    if model_dir and (Path(model_dir) / "conv_model.pt").exists():
        print(f"[conv] loading conversation model from {model_dir}")
        return ConvEngine(Path(model_dir))
    print("[conv] no conv_model.pt found -> Brain uses rule-based stage tracking (train it with the training notebook)")
    return None
