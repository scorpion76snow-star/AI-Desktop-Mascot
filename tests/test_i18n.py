from app.core.i18n import tr_text


def test_english_menu():
    assert tr_text("聊天", "en") == "Chat"
    assert tr_text("Boss", "en") == "Boss"


def test_chinese_reverse():
    assert tr_text("Chat", "zh") == "聊天"
