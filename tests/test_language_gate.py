from app.chat.quality import validate_reply, fallback_reply


def test_english_mode_rejects_chinese():
    ok, reason = validate_reply("hello", "你好", language="en")
    assert ok is False
    assert reason == "language"


def test_english_fallback_is_english():
    assert fallback_reply("你好", "en").startswith("I didn't")
