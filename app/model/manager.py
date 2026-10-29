# -*- coding: utf-8 -*-
"""Model switching: local GatedLM or OpenAI-compatible API."""

import os
import sys

from app.core.config import MODELS_DIR, PROJECT_DIR


class ModelManager:
    def __init__(self, settings):
        self.settings = settings
        self.backend = None
        self.profile = None

    def _build(self):
        profile = self.settings.get("model_profile", "local")
        if profile == self.profile and self.backend is not None:
            return self.backend
        if profile == "openai":
            from app.model.openai_backend import OpenAIBackend
            backend = OpenAIBackend(self.settings)
        else:
            if PROJECT_DIR not in sys.path:
                sys.path.insert(0, PROJECT_DIR)
            from app.model.local.service import ModelService
            backend = ModelService(model_dir=MODELS_DIR)
        self.backend = backend
        self.profile = profile
        return backend

    def load(self):
        return self._build().load()

    def status_text(self):
        try:
            s = self._build().status()
        except Exception as exc:
            return f"Error: {exc}"
        if s.get("loaded"):
            lang = self.settings.get("language", "en")
            if lang == "en":
                return f"Loaded · {s.get('device', '')}".strip()
            return f"已加载 · {s.get('device', '')}".strip()
        return "Not loaded" if self.settings.get("language", "en") == "en" else "未加载"

    def reply_messages(self, system, turns, max_new=120):
        return self._build().reply_messages(system, turns, max_new=max_new)

    def reply(self, user, system=None, max_new=120):
        return self.reply_messages(system, [("user", user)], max_new=max_new)

    def count_tokens(self, text):
        try:
            return self._build().count_tokens(text)
        except Exception:
            return max(1, len(text or "") // 3)
