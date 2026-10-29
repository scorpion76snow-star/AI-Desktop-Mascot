# -*- coding: utf-8 -*-
"""App paths and JSON settings under %APPDATA%/YunPet."""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # app/core
APP_DIR = os.path.dirname(BASE_DIR)                            # app
if getattr(sys, "frozen", False):
    PROJECT_DIR = os.path.dirname(sys.executable)
else:
    PROJECT_DIR = os.path.dirname(APP_DIR)

MODELS_DIR = os.path.join(PROJECT_DIR, "models", "local")
VOICES_DIR = os.path.join(PROJECT_DIR, "voices")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
APP_DATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "YunPet")
CONFIG_PATH = os.path.join(APP_DATA, "config.json")
SKINS_DIR = os.path.join(APP_DATA, "skins")

DEFAULTS = {
    "app_name": "YunPet",
    "language": "en",
    "pet_x": None,
    "pet_y": None,
    "skin": "default",
    "voice_enabled": False,
    "voice_chat_enabled": False,
    "voice_mail_enabled": False,
    "voice_pet_enabled": False,
    "voice_volume": 0.9,
    "voice_profile": "default",
    "quiet_hours": "",
    "mail_poll_seconds": 60,
    "mail_provider": "",
    "mail_client_id": "",
    "mail_accounts": [],
    "model_profile": "local",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4o-mini",
    "openai_key_ref": "YunPet/openai",
    "openai_temperature": 0.7,
    "openai_max_tokens": 300,
    "voice_zh_model": "voice_zh_huayan.onnx",
    "voice_zh_config": "voice_zh_huayan.json",
    "voice_en_model": "voice_en_alba.onnx",
    "voice_en_config": "voice_en_alba.json",
    "voice_zh_length_scale": 1.10,
    "voice_en_length_scale": 1.00,
    "include_subject_in_voice": True,
    "repeat_unread_after_seconds": 120,
}


class Settings:
    def __init__(self, path=None):
        self.path = path or CONFIG_PATH
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self.data.update(raw)
                if not raw.get("_voice_default_off"):
                    for k in ("voice_enabled", "voice_chat_enabled",
                              "voice_mail_enabled", "voice_pet_enabled"):
                        self.data[k] = False
                    self.data["_voice_default_off"] = True
                    self.save()
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        # migrate the old single-mailbox settings
        if not self.data.get("mail_accounts") and self.data.get("mail_provider"):
            self.data["mail_accounts"] = [{
                "label": "default",
                "provider": self.data.get("mail_provider"),
                "client_id": self.data.get("mail_client_id", ""),
            }]
        return self

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
