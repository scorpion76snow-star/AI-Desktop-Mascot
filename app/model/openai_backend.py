# -*- coding: utf-8 -*-
"""OpenAI chat-completions backend."""

import json
import urllib.error
import urllib.request

from app.model.base import ModelBackend


class OpenAIBackend(ModelBackend):
    name = "openai"

    def __init__(self, settings):
        self.settings = settings

    def _key(self):
        ref = self.settings.get("openai_key_ref", "YunPet/openai")
        try:
            import keyring
            key = keyring.get_password("YunPet", ref)
        except Exception:
            key = None
        if not key:
            raise RuntimeError("OpenAI API key is not set.")
        return key

    def load(self):
        self._key()
        return self

    def status(self):
        return {"loaded": True, "device": "cloud",
                "model": self.settings.get("openai_model", "gpt-4o-mini")}

    def count_tokens(self, text):
        return max(1, len(text or "") // 3)

    def reply_messages(self, system, turns, max_new=120):
        base = self.settings.get("openai_base_url", "https://api.openai.com/v1").rstrip("/")
        model = self.settings.get("openai_model", "gpt-4o-mini")
        lang = self.settings.get("language", "en")
        sys_prompt = (system or "").strip()
        sys_prompt += ("\nAlways answer in English." if lang == "en"
                       else "\n请始终用中文回答。")
        messages = [{"role": "system", "content": sys_prompt}]
        for turn in turns:
            role = turn.get("role") if isinstance(turn, dict) else turn[0]
            content = turn.get("content") if isinstance(turn, dict) else turn[1]
            messages.append({"role": role, "content": content})
        payload = {
            "model": model,
            "messages": messages,
            "temperature": float(self.settings.get("openai_temperature", 0.7)),
            "max_tokens": max(32, min(int(max_new), int(self.settings.get("openai_max_tokens", 300)))),
        }
        req = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._key()}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"OpenAI HTTP {exc.code}: {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
        try:
            text = data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise RuntimeError("OpenAI response has no message content.") from exc
        return text, [1.0, 0.0, 0.0], "REPLY"
