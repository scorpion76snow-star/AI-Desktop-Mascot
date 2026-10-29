# -*- coding: utf-8 -*-
"""Cheap deterministic quality gate for generated chat replies."""

import re
from difflib import SequenceMatcher

BAD_PHRASES = (
    "周末都没怎么到",
    "我也没怎么到",
    "我这边一直是断的",
)

PREF_PHRASES = (
    "记下了，本次对话按这个偏好",
    "本次对话按这个偏好",
)
PREF_KEYS = ("偏好", "以后", "记住", "称呼", "长度", "抄送", "语气", "格式")

# If the user clearly asks about one of these topics, a reply that contains
# none of the expected words is almost certainly off-topic.
TOPIC_WORDS = [
    (("天气", "好冷", "降温", "下雨", "好热"),
     ("天气", "冷", "热", "雨", "晴", "风", "降温", "外套", "伞", "温度")),
    (("出门", "上班", "路上"),
     ("路上", "小心", "慢", "带", "伞", "外面", "注意", "外套")),
    (("累", "困", "疲惫"),
     ("累", "歇", "休息", "睡", "喘口气", "辛苦")),
    (("开心", "高兴", "好事"),
     ("开心", "高兴", "好事", "真好", "笑", "庆祝")),
    (("伤心", "难过"),
     ("怎么", "听", "说", "难过", "伤心", "陪着")),
]


def _norm(text):
    return re.sub(r"\s+", "", (text or "").strip().lower())


def validate_reply(user, reply, previous=None, context="", language=None):
    """Return (ok, reason)."""
    text = (reply or "").strip()
    if len(text) < 2:
        return False, "empty"
    if language == "en" and re.search(r"[\u4e00-\u9fff]", text):
        return False, "language"
    if any(p in text for p in BAD_PHRASES):
        return False, "known_bad"
    if any(p in text for p in PREF_PHRASES) and not any(k in user for k in PREF_KEYS):
        return False, "unexpected_preference"
    for triggers, expected in TOPIC_WORDS:
        if any(k in user for k in triggers) and not any(k in text for k in expected):
            return False, "topic_mismatch"
    n = _norm(text)
    for old in (previous or [])[-3:]:
        old_n = _norm(old)
        if old_n and (n == old_n or SequenceMatcher(None, n, old_n).ratio() > 0.88):
            return False, "repeat"
    # If a long reply has no overlap at all with the user, it is likely off-topic.
    if len(n) > 24 and len(_norm(user)) > 4:
        common = set(n) & set(_norm(user))
        if len(common) < 2:
            return False, "off_topic"
    return True, ""


def fallback_reply(user, language=None):
    if language == "zh" or (language is None and any("\u4e00" <= ch <= "\u9fff" for ch in user)):
        return "我没听明白，您再说一遍？"
    return "I didn't quite catch that — could you say it again?"
