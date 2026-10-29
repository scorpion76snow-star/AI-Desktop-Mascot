# -*- coding: utf-8 -*-
"""Post-hoc fact check + safe fallback for generated replies.

    from app.chat.factcheck import check
    bad = check(reply, system + "\n" + user)   # list of unsupported facts
    if bad:
        reply = "我需要再核对一下这项信息，先不替您确认。"

This is deliberately conservative: it only looks for dates/numbers/weekdays
and a fixed name pool.  It catches the common failure where a 48M model
rewrites "团队复盘" into "去会议" or invents a time.
"""

import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.constants import NAMES_EN, NAMES_ZH, WEEKDAYS_EN, WEEKDAYS_ZH

DIGITS = re.compile(r"\d+")


def check(reply, context):
    bad = []
    for d in DIGITS.findall(reply):
        if d not in context:
            bad.append(f"number:{d}")
    for wd in WEEKDAYS_ZH:
        if wd in reply and wd not in context:
            bad.append(f"weekday:{wd}")
    for wd in WEEKDAYS_EN:
        if wd.lower() in reply.lower() and wd.lower() not in context.lower():
            bad.append(f"weekday:{wd}")
    for name in NAMES_ZH:
        if name in reply and name not in context:
            bad.append(f"name:{name}")
    for name in NAMES_EN:
        if name in reply and name.lower() not in context.lower():
            bad.append(f"name:{name}")
    return bad


def safe(reply, context, fallback):
    return fallback if check(reply, context) else reply
