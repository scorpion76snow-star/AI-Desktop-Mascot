# -*- coding: utf-8 -*-
"""Lazy model service used by the desktop app.

M0 skeleton: load/unload and a basic greedy reply.  Structured routing,
permissions, fact-check and guard stay in the app/chat layer for now.
"""

import os
import threading

import torch
import torch.nn.functional as F
from tokenizers import Tokenizer

from .gated_lm import GatedLM, Cfg

PAD, BOS, EOS = 0, 1, 2
SYSTEM, USER, ASSISTANT, END = 12, 13, 14, 15
PROTECTED = {ASSISTANT, END, EOS}
GATE_NAMES = ["REPLY", "ESCALATE", "IGNORE"]


class ModelService:
    def __init__(self, model_dir=None, device=None):
        self.model_dir = model_dir or os.path.dirname(os.path.abspath(__file__))
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self._lock = threading.Lock()

    @property
    def loaded(self):
        return self.model is not None and self.tokenizer is not None

    def status(self):
        return {
            "loaded": self.loaded,
            "device": self.device,
            "model_dir": self.model_dir,
        }

    def load(self):
        with self._lock:
            if self.loaded:
                return self
            ckpt = os.path.join(self.model_dir, "sft_best.pt")
            tok_path = os.path.join(self.model_dir, "tokenizer.json")
            ck = torch.load(ckpt, map_location="cpu", weights_only=False)
            cfg = Cfg(**ck["cfg"])
            model = GatedLM(cfg)
            model.load_state_dict(ck["model"])
            model.to(self.device).eval()
            self.model = model
            self.tokenizer = Tokenizer.from_file(tok_path)
            return self

    def unload(self):
        with self._lock:
            self.model = None
            self.tokenizer = None
            if self.device == "cuda":
                torch.cuda.empty_cache()

    def _encode(self, text):
        return self.tokenizer.encode(text, add_special_tokens=False).ids

    def count_tokens(self, text):
        self.load()
        return len(self._encode(text or ""))

    def _prompt(self, user, system=None):
        return self._prompt_messages(system, [("user", user)])

    def _prompt_messages(self, system, turns):
        ids = [BOS]
        if system:
            ids += [SYSTEM] + self._encode(system) + [END]
        for turn in turns:
            if isinstance(turn, dict):
                role, content = turn.get("role"), turn.get("content", "")
            else:
                role, content = turn[0], turn[1]
            tag = USER if role == "user" else ASSISTANT
            ids += [tag] + self._encode(content) + [END]
        return ids

    @torch.inference_mode()
    def reply(self, user, system=None, max_new=120):
        """Return (text, probs, gate_name). text is None for non-REPLY."""
        return self.reply_messages(system, [("user", user)], max_new=max_new)

    @torch.inference_mode()
    def reply_messages(self, system, turns, max_new=120):
        """Multi-turn reply. turns = [(role, content), ...], last is current user."""
        self.load()
        ids = self._prompt_messages(system, turns)
        if len(ids) > self.model.c.max_len - 8:
            raise ValueError(f"prompt too long: {len(ids)} > {self.model.c.max_len - 8}")
        idx = torch.tensor([ids], dtype=torch.long, device=self.device)
        x = self.model.trunk(idx)
        probs = F.softmax(self.model.gate(x[:, -1]).float(), -1)[0].tolist()
        gate = max(range(3), key=lambda i: probs[i])
        if gate != 0:
            return None, probs, GATE_NAMES[gate]

        seq = list(ids)
        for _ in range(max_new):
            if len(seq) >= self.model.c.max_len - 1:
                break
            idx = torch.tensor([seq], dtype=torch.long, device=self.device)
            logits = self.model.lm_head(self.model.trunk(idx))[0, -1].float()
            for sid in range(28):
                if sid not in PROTECTED:
                    logits[sid] = -float("inf")
            nxt = int(logits.argmax())
            seq.append(nxt)
            if nxt in (END, EOS):
                break
        text = self.tokenizer.decode(seq[len(ids):], skip_special_tokens=True).strip()
        return text, probs, GATE_NAMES[gate]
