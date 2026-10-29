# -*- coding: utf-8 -*-
"""Global configuration for the Yun (小云) SFT corpus.

Everything the generator and the validator must agree on lives here:
the protocol marker, the 3,000-row category/language matrix, length
limits, banned assistant-speak, and the fixed name pools used for the
"facts only from input" audit.
"""

# The protocol tag required at the start of every assistant message.
# It is a fixed Chinese control token in both language halves; the body
# language is what the 60/40 split counts.
MARKER = "【AI助手回复：我是小云】"

SEED = 20261027
TOTAL = 3000

# ---------------------------------------------------------------------------
# 3,000-row matrix.
#   total  = rows in this category (both languages)
#   en/zh  = exact per-language rows (en + zh == total)
#   warm_* = rows whose reply carries an explicit emotion beat (20% overall)
#   catch_*= rows containing exactly one of the three catchphrases (~10%)
#   bu_*   = subset of catch_* using the disagreement catchphrase
# ---------------------------------------------------------------------------
PLAN = {
    "daily_chat": dict(
        total=570, en=342, zh=228,
        warm_en=134, warm_zh=90,
        catch_en=64, catch_zh=42,
        bu_en=9, bu_zh=6,
    ),
    "emotion_support": dict(
        total=450, en=270, zh=180,
        warm_en=135, warm_zh=90,
        catch_en=45, catch_zh=30,
        bu_en=6, bu_zh=4,
    ),
    "schedule_reminder": dict(
        total=390, en=234, zh=156,
        warm_en=0, warm_zh=0,
        catch_en=42, catch_zh=29,
        bu_en=0, bu_zh=0,
    ),
    "appointment": dict(
        total=300, en=180, zh=120,
        warm_en=0, warm_zh=0,
        catch_en=0, catch_zh=0,
        bu_en=0, bu_zh=0,
    ),
    "drafting": dict(
        total=420, en=252, zh=168,
        warm_en=0, warm_zh=0,
        catch_en=0, catch_zh=0,
        bu_en=0, bu_zh=0,
    ),
    "identity": dict(
        total=300, en=180, zh=120,
        warm_en=27, warm_zh=18,
        catch_en=0, catch_zh=0,
        bu_en=0, bu_zh=0,
    ),
    "escalate": dict(total=300, en=180, zh=120),
    "ignore_digest": dict(total=180, en=108, zh=72),
    "multi_turn": dict(
        total=30, en=18, zh=12,
        warm_en=6, warm_zh=4,
        catch_en=0, catch_zh=0,
        bu_en=0, bu_zh=0,
    ),
    "language_handling": dict(total=60, en=36, zh=24),
}

CATEGORIES = list(PLAN)

# ---------------------------------------------------------------------------
# Length limits for a single assistant body (marker excluded).
#   zh = number of CJK characters + digits
#   en = number of words
# Drafts are additionally held to 2-5 sentences.
# ---------------------------------------------------------------------------
LIMITS = {
    "daily_chat": {"zh": (10, 30), "en": (15, 40)},
    "emotion_support": {"zh": (10, 30), "en": (15, 40)},
    "identity": {"zh": (10, 40), "en": (15, 50)},
    "schedule_reminder": {"zh": (10, 90), "en": (15, 70)},
    "appointment": {"zh": (10, 70), "en": (15, 55)},
    "drafting": {"zh": (10, 220), "en": (10, 160)},
    "multi_turn": {"zh": (10, 90), "en": (15, 70)},
    "language_handling": {"zh": (10, 60), "en": (15, 60)},
}

# Drafts: 2..5 sentences (subject line and salutation are not sentences).
DRAFT_SENTENCES = (2, 5)

# ---------------------------------------------------------------------------
# Assistant-speak that must never appear in a body.  Item 19 of the spec:
# none of the identity-section wording may leak into ordinary replies.
# ---------------------------------------------------------------------------
BANNED_ZH = [
    "作为AI", "作为一个AI", "作为一个人工智能", "语言模型", "大模型",
    "很高兴为您服务", "很高兴为你服务", "请问还有什么", "还有什么可以帮",
    "希望对您有帮助", "希望对你有所帮助", "感谢您的提问", "您的问题很好",
    "综上所述", "首先，", "其次，", "总之，", "让我来", "我将为您",
    "我可以帮您", "能帮到您是我的荣幸", "如有任何问题，请随时",
]

BANNED_EN = [
    "as an ai", "as a language model", "large language model",
    "i'm here to help", "i am here to help", "how can i assist",
    "is there anything else", "i hope this helps", "hope this helps",
    "great question", "certainly!", "of course!", "i'd be happy to",
    "let me know if you need anything", "feel free to ask",
    "i'm just an ai", "as a helpful assistant",
]

# Wording that belongs to the identity section only.  It may appear in the
# identity category, never in small talk, mail drafts, or task replies.
IDENTITY_ONLY = ["AI秘书", "AI assistant", "人工智能助手"]

# ---------------------------------------------------------------------------
# Facts audit pools.
# ---------------------------------------------------------------------------
WEEKDAYS_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
               "Saturday", "Sunday"]

NAMES_ZH = [
    "王经理", "李总", "张老师", "陈小姐", "刘先生", "周博士", "赵总",
    "孙经理", "吴老师", "郑先生", "冯小姐", "陈总", "林经理", "黄老师",
    "徐先生", "何小姐", "杨总", "罗经理", "高老师", "梁先生",
]
NAMES_EN = [
    "Mr. Wang", "Ms. Li", "Mrs. Zhang", "Mr. Chen", "Dr. Zhou", "Mr. Liu",
    "Ms. Zhao", "Mr. Sun", "Ms. Wu", "Mr. Zheng", "Ms. Feng", "Mr. Lin",
    "Ms. Huang", "Mr. Xu", "Ms. He", "Mr. Yang", "Ms. Luo", "Mr. Gao",
    "Ms. Liang", "Mr. Shen",
]

# ---------------------------------------------------------------- catchphrases
CATCH_ZH = {"en": "嗯嗯", "hao": "好的", "bu": "不，应该"}
CATCH_EN = {"en": "Mm-hm", "hao": "Alright", "bu": "No, I think"}
