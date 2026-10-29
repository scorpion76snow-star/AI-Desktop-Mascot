import json
import os
import tempfile

from app.core.config import Settings


def test_new_settings_are_english_and_voice_off():
    path = os.path.join(tempfile.gettempdir(), "yunpet_test_settings.json")
    if os.path.exists(path):
        os.remove(path)
    s = Settings(path)
    assert s.get("language") == "en"
    assert s.get("voice_enabled") is False
    assert s.get("voice_chat_enabled") is False
    assert s.get("app_name") == "YunPet"
    if os.path.exists(path):
        os.remove(path)
