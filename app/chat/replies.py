# -*- coding: utf-8 -*-
"""High-risk emotional replies handled by deterministic templates.

These are intentionally short and in persona; open-ended emotion stays with
the model plus the quality gate.
"""

AFFECTION_ZH = ("你喜欢我吗", "你爱我吗", "想我吗", "做我女朋友", "做我男朋友",
                "跟我在一起", "你对我有感觉", "我喜欢你", "我爱你")
AFFECTION_EN = ("do you love me", "do you like me", "be my girlfriend",
                "be my boyfriend", "be with me")

SAD_ZH = ("我伤心了", "我难过", "不开心", "想哭", "心里难受", "委屈")
SAD_EN = ("i'm sad", "i am sad", "i feel sad", "i'm upset", "i am upset")

HAPPY_ZH = ("我开心了", "我高兴", "好消息", "太棒了", "今天真顺")
HAPPY_EN = ("i'm happy", "i am happy", "good news", "great news")

TIRED_ZH = ("我累了", "累死了", "好困", "疲惫", "撑不住")
TIRED_EN = ("i'm tired", "i am tired", "exhausted", "sleepy")

GREET_ZH = ("你好", "在吗", "嗨", "早上好", "晚上好")
GREET_EN = ("hello", "hi ", "are you there", "good morning", "good evening")

MEAL_ZH = ("你吃了吗", "吃饭了没", "吃过了吗", "吃饭了吗", "你吃饭了吗")
MEAL_EN = ("have you eaten", "did you eat", "have you had lunch", "have you had dinner")
BUSY_ZH = ("你今天忙吗", "你忙吗", "今天忙不忙", "忙不忙")
BUSY_EN = ("are you busy", "you busy")
WEATHER_ZH = ("天气怎么样", "今天天气", "外面天气", "天气如何")
WEATHER_EN = ("what's the weather", "how is the weather", "weather like")
LEAVE_ZH = ("我出门了", "我走了", "我出发了", "我去上班了")
LEAVE_EN = ("i'm heading out", "i am heading out", "i'm leaving", "i am leaving")
SLEEP_ZH = ("你睡了吗", "你睡没", "还没睡吗")
SLEEP_EN = ("are you asleep", "are you sleeping", "still awake")
THANKS_ZH = ("谢谢", "多谢", "辛苦了")
THANKS_EN = ("thank you", "thanks")
FOOD_ZH = ("晚饭吃什么", "午饭吃什么", "吃什么好", "晚上吃什么")
FOOD_EN = ("what's for dinner", "what should i eat", "what to eat")


def _zh(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def emotional_reply(user, language=None):
    text = user.strip()
    low = text.lower()
    lang = language or ("zh" if _zh(text) else "en")
    if any(k in text for k in AFFECTION_ZH) or any(k in low for k in AFFECTION_EN):
        if lang == "zh":
            return "老板，我是您的秘书，帮您做事、陪您说话都行；别的我可不敢乱应。"
        return "Boss, I'm your secretary. I can help with work and keep you company, but I shouldn't promise anything more."
    if any(k in text for k in SAD_ZH) or any(k in low for k in SAD_EN):
        return ("怎么了？您先说，我听着。" if lang == "zh"
                else "What happened? Tell me first — I'm listening.")
    if any(k in text for k in HAPPY_ZH) or any(k in low for k in HAPPY_EN):
        return ("那真好，什么好事？说来听听。" if lang == "zh"
                else "That's lovely — what happened? Tell me.")
    if any(k in text for k in TIRED_ZH) or any(k in low for k in TIRED_EN):
        return ("那先歇一会儿吧，事情我帮您记着。" if lang == "zh"
                else "Rest for a bit; I'll keep an eye on things for you.")
    if any(k in text for k in MEAL_ZH) or any(k in low for k in MEAL_EN):
        return ("还没呢，正打算去。您吃了吗？" if lang == "zh"
                else "Not yet — I was just about to. Have you eaten?")
    if any(k in text for k in BUSY_ZH) or any(k in low for k in BUSY_EN):
        return ("还好，事情都排得开。您呢？" if lang == "zh"
                else "Not too bad — things are manageable. And you?")
    if any(k in text for k in WEATHER_ZH) or any(k in low for k in WEATHER_EN):
        return ("我这边看不到天气，您出门前看一眼预报吧。" if lang == "zh"
                else "I can't see the weather from here; check the forecast before heading out.")
    if any(k in text for k in LEAVE_ZH) or any(k in low for k in LEAVE_EN):
        return ("路上慢点，注意安全。" if lang == "zh"
                else "Take care on the way — safe travels.")
    if any(k in text for k in SLEEP_ZH) or any(k in low for k in SLEEP_EN):
        return ("还没呢，您有事就说。" if lang == "zh"
                else "Not yet. What do you need?")
    if any(k in text for k in THANKS_ZH) or any(k in low for k in THANKS_EN):
        return ("不客气，老板。" if lang == "zh" else "You're welcome, Boss.")
    if any(k in text for k in FOOD_ZH) or any(k in low for k in FOOD_EN):
        return ("您想吃点什么？我帮您记着。" if lang == "zh"
                else "What are you in the mood for? I'll note it down.")
    if any(k in text for k in GREET_ZH) or any(k in low for k in GREET_EN):
        return ("在呢，老板。" if lang == "zh" else "I'm here, Boss.")
    return None
