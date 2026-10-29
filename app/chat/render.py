# -*- coding: utf-8 -*-
"""Deployment-side deterministic renderer.

The SFT model should not be trusted to copy facts.  Give this module the same
structured data that produced the `system` block, and it answers schedule /
to-do questions exactly.  The LM is only used for free-form phrasing.

    from render import render_system, schedule_answer, todo_answer
    system = render_system(now, events, todos, prefs, "zh")
    reply  = schedule_answer(now, events, {"type": "day", "date": "2026-10-28"}, "zh")
"""

import re
from datetime import datetime, timedelta

WEEK_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
WEEK_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _d(s):
    return s if isinstance(s, datetime) else datetime.fromisoformat(s)


def _date(s):
    return s if isinstance(s, type(datetime.now().date())) else datetime.fromisoformat(str(s)).date()


def cn_date(d):
    return f"{d.month}月{d.day}日"


def en_date(d):
    return f"{d.day} {d.strftime('%b')}"


def day_label(d, lang):
    if lang == "zh":
        return f"{cn_date(d)} {WEEK_CN[d.weekday()]}"
    return f"{WEEK_EN[d.weekday()]} {en_date(d)}"


def _now_label(now, lang):
    if lang == "zh":
        return f"{now.year}-{now.month:02d}-{now.day:02d} {WEEK_CN[now.weekday()]} {now:%H:%M}"
    return f"{now.year}-{now.month:02d}-{now.day:02d} {WEEK_EN[now.weekday()]} {now:%H:%M}"


def render_system(now, events=None, todos=None, prefs=None, lang="zh"):
    lines = [f"【现在】{_now_label(now, lang)}" if lang == "zh" else f"[Now] {_now_label(now, lang)}"]
    if events:
        lines.append("【日历】" if lang == "zh" else "[Calendar]")
        for e in sorted(events, key=lambda x: (x["date"], x["start"])):
            d = _date(e["date"])
            if lang == "zh":
                place = f"（{e['place']}）" if e.get("place") else ""
                lines.append(f"- {day_label(d, lang)} {e['start']}-{e['end']} {e['title']}{place}")
            else:
                place = f" ({e['place']})" if e.get("place") else ""
                lines.append(f"- {day_label(d, lang)}, {e['start']}-{e['end']} — {e['title']}{place}")
    if todos:
        lines.append("【待办】" if lang == "zh" else "[To-do]")
        for t in todos:
            d = _date(t["due"])
            if lang == "zh":
                lines.append(f"- {day_label(d, lang)} {t.get('time','17:00')} 前 {t['text']}（{t['priority']}）")
            else:
                lines.append(f"- by {day_label(d, lang)} {t.get('time','17:00')} — {t['text']} ({t['priority']})")
    if prefs:
        lines.append("【偏好】" if lang == "zh" else "[Preferences]")
        if lang == "zh":
            names = {"address": "称呼", "signoff": "结尾", "sign-off": "结尾",
                     "length": "长度", "cc": "抄送", "tone": "语气",
                     "format": "格式", "date": "日期"}
            lines.append("；".join(f"{names.get(k, k)}：{v}" for k, v in prefs.items()))
        else:
            lines.append("; ".join(f"{k}: {v}" for k, v in prefs.items()))
    return "\n".join(lines)


def _events_on(events, d):
    return [e for e in events if _date(e["date"]) == d]


def _list(events, lang):
    if lang == "zh":
        return "，".join(f"{e['start']} {e['title']}（{e['place']}）" for e in events)
    return ", ".join(f"{e['title']} at {e['start']} ({e['place']})" for e in events)


def _num(n, lang):
    cn = ["零", "一", "两", "三", "四", "五", "六", "七", "八", "九", "十"]
    en = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
    return cn[n] if lang == "zh" else en[n]


def schedule_answer(now, events, q, lang="zh"):
    typ = q.get("type")
    if typ == "day":
        d = _date(q["date"])
        es = _events_on(events, d)
        label = day_label(d, lang)
        if not es:
            return (f"{label}没有安排，您可以安心做自己的事。" if lang == "zh"
                    else f"{label} is clear, so you have the day to yourself.")
        if len(es) == 1:
            e = es[0]
            return (f"{label}有{e['title']}，{e['start']}开始，地点在{e['place']}。" if lang == "zh"
                    else f"{label} you have the {e['title']} at {e['start']}, at the {e['place']}.")
        return (f"{label}有{_num(len(es), lang)}项：{_list(es, lang)}。" if lang == "zh"
                else f"{label} you have {_num(len(es), lang)} things: {_list(es, lang)}.")
    if typ == "week":
        end = now.date() + timedelta(days=6)
        es = [e for e in events if now.date() <= _date(e["date"]) <= end]
        if not es:
            return "这周没有安排。" if lang == "zh" else "There is nothing on the calendar this week."
        return (f"这周有{_num(len(es), lang)}项：{_list(es, lang)}。" if lang == "zh"
                else f"This week you have {_num(len(es), lang)} things: {_list(es, lang)}.")
    if typ == "time":
        e = next(e for e in events if e["title"] == q["title"])
        return (f"{e['title']}在{day_label(_date(e['date']), lang)} {e['start']}开始。" if lang == "zh"
                else f"The {e['title']} starts at {e['start']} on {day_label(_date(e['date']), lang)}.")
    if typ == "place":
        e = next(e for e in events if e["title"] == q["title"])
        return (f"{e['title']}地点是{e['place']}。" if lang == "zh"
                else f"The {e['title']} is at the {e['place']}.")
    if typ == "count":
        d1 = now.date()
        d2 = d1 + timedelta(days=q.get("days", 7) - 1)
        n = sum(1 for e in events if d1 <= _date(e["date"]) <= d2)
        return (f"一共{_num(n, lang)}项安排。" if lang == "zh"
                else f"There are {_num(n, lang)} items on the calendar.")
    raise ValueError(f"unknown schedule query {typ}")


def todo_answer(now, items, q, lang="zh"):
    typ = q.get("type")
    if typ == "day":
        d = _date(q.get("date", now.date()))
        due = [t for t in items if _date(t["due"]) == d]
        label = day_label(d, lang)
        if not due:
            return f"{label}没有待办。" if lang == "zh" else f"Nothing is due on {label}."
        if lang == "zh":
            return f"{label}有{_num(len(due), lang)}项待办：" + "；".join(f"{t['text']}（{t['priority']}）" for t in due) + "。"
        return f"{label} you have {_num(len(due), lang)} to-do{'s' if len(due) != 1 else ''}: " + "; ".join(f"{t['text']} ({t['priority']})" for t in due) + "."
    if typ == "top":
        order = {"高": 0, "high": 0, "中": 1, "medium": 1, "低": 2, "low": 2}
        top = sorted(items, key=lambda t: (_date(t["due"]), order.get(t["priority"], 3)))[0]
        return (f"先做“{top['text']}”，{day_label(_date(top['due']), lang)} {top['time']} 前到期，优先级{top['priority']}。"
                if lang == "zh" else
                f"Start with “{top['text']}”: due by {day_label(_date(top['due']), lang)} {top['time']}, marked {top['priority']}.")
    raise ValueError(f"unknown todo query {typ}")


# --------------------------------------------------------------------------- parse system block
_MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
           "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def _parse_now(line):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2}).*?(\d{2}):(\d{2})", line)
    if not m:
        return None
    y, mo, d, h, mi = map(int, m.groups())
    return datetime(y, mo, d, h, mi)


def _mk_date(y, mo, d, now):
    if now:
        if mo < now.month - 6:
            y += 1
        elif mo > now.month + 6:
            y -= 1
    return datetime(y, mo, d).date()


def _parse_event(s, now):
    m = re.match(r"^- (\d{1,2})月(\d{1,2})日\s+周[一二三四五六日天]\s+"
                 r"(\d{2}):(\d{2})-(\d{2}):(\d{2})\s+(.+?)(?:（(.+)）)?$", s)
    if m:
        mo, d, sh, sm, eh, em, title, place = m.groups()
        year = now.year if now else datetime.now().year
        return {"date": _mk_date(year, int(mo), int(d), now),
                "start": f"{sh}:{sm}", "end": f"{eh}:{em}",
                "title": title.strip(), "place": (place or "").strip()}
    m = re.match(r"^- \w{3} (\d{1,2}) (\w{3}), (\d{2}):(\d{2})-(\d{2}):(\d{2}) — "
                 r"(.+?)(?: \((.+)\))?$", s)
    if m:
        d, mon, sh, sm, eh, em, title, place = m.groups()
        mo = _MONTHS.get(mon, 1)
        year = now.year if now else datetime.now().year
        return {"date": _mk_date(year, mo, int(d), now),
                "start": f"{sh}:{sm}", "end": f"{eh}:{em}",
                "title": title.strip(), "place": (place or "").strip()}
    return None


def _parse_todo(s, now):
    m = re.match(r"^- (\d{1,2})月(\d{1,2})日\s+周[一二三四五六日天]\s+"
                 r"(\d{2}):(\d{2}) 前 (.+?)（(高|中|低)）$", s)
    if m:
        mo, d, h, mi, text, prio = m.groups()
        year = now.year if now else datetime.now().year
        return {"due": _mk_date(year, int(mo), int(d), now), "time": f"{h}:{mi}",
                "text": text.strip(), "priority": prio}
    m = re.match(r"^- by \w{3} (\d{1,2}) (\w{3}) (\d{2}):(\d{2}) — "
                 r"(.+?) \((high|medium|low)\)$", s)
    if m:
        d, mon, h, mi, text, prio = m.groups()
        year = now.year if now else datetime.now().year
        return {"due": _mk_date(year, _MONTHS.get(mon, 1), int(d), now),
                "time": f"{h}:{mi}", "text": text.strip(), "priority": prio}
    return None


def parse_system(system):
    """Parse the 【现在】/【日历】/【待办】 text block back into structures."""
    if not system:
        return None
    now, events, todos, section = None, [], [], None
    for raw in system.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("【现在】") or s.startswith("[Now]"):
            now = _parse_now(s)
            section = None
        elif s in ("【日历】", "[Calendar]") or s.startswith("【日历") or s.startswith("[Calendar"):
            section = "cal"
        elif s in ("【待办】", "[To-do]") or s.startswith("【待办") or s.startswith("[To-do"):
            section = "todo"
        elif s.startswith("【偏好】") or s.startswith("[Preferences]"):
            section = "pref"
        elif s.startswith("- "):
            if section == "cal":
                e = _parse_event(s, now)
                if e:
                    events.append(e)
            elif section == "todo":
                t = _parse_todo(s, now)
                if t:
                    todos.append(t)
    if not now:
        if events or todos:
            return {"error": "missing_now"}
        return None
    if not events and not todos:
        return None
    return {"now": now, "events": events, "todos": todos}


# --------------------------------------------------------------------------- routing
_WEEK_NAMES_CN = "一二三四五六日"


def _lang_of(user):
    return "zh" if re.search(r"[\u4e00-\u9fff]", user) else "en"


def _target_date(user, now, lang):
    text = user.lower()
    d0 = now.date()

    # explicit date first: 12月14日 / 2 Nov / Nov 2
    m = re.search(r"(\d{1,2})月(\d{1,2})日", user)
    if m:
        return _mk_date(now.year, int(m.group(1)), int(m.group(2)), now)
    m = re.search(r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", text)
    if m:
        mon = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
               "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}[m.group(2)]
        return _mk_date(now.year, mon, int(m.group(1)), now)
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})", text)
    if m:
        mon = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
               "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}[m.group(1)]
        return _mk_date(now.year, mon, int(m.group(2)), now)

    if "今天" in user or "today" in text:
        return d0
    if "明天" in user or "tomorrow" in text:
        return d0 + timedelta(days=1)
    if "后天" in user:
        return d0 + timedelta(days=2)

    m = re.search(r"下周([一二三四五六日天])", user)
    if m:
        wd = _WEEK_NAMES_CN.index(m.group(1).replace("天", "日")) if m.group(1) != "天" else 6
        monday = d0 - timedelta(days=d0.weekday()) + timedelta(days=7)
        return monday + timedelta(days=wd)
    m = re.search(r"(?:这|本)?周([一二三四五六日天])", user)
    if m:
        wd = 6 if m.group(1) == "天" else _WEEK_NAMES_CN.index(m.group(1))
        monday = d0 - timedelta(days=d0.weekday())
        d = monday + timedelta(days=wd)
        if d < d0:
            d += timedelta(days=7)
        return d

    en = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, name in enumerate(en):
        if name in text:
            monday = d0 - timedelta(days=d0.weekday())
            d = monday + timedelta(days=i)
            if "next " + name in text:
                d += timedelta(days=7)
            elif d < d0:
                d += timedelta(days=7)
            return d
    return None


def _period_of_text(user):
    if "上午" in user or "morning" in user.lower():
        return "上午" if "上午" in user else "morning"
    if "下午" in user or "afternoon" in user.lower():
        return "下午" if "下午" in user else "afternoon"
    if "晚上" in user or "evening" in user.lower():
        return "晚上" if "晚上" in user else "evening"
    return None


def _event_period(t):
    h = int(t.split(":")[0])
    return "morning" if h < 12 else ("afternoon" if h < 18 else "evening")


def appointment_answer(ctx, user, lang):
    d = _target_date(user, ctx["now"], lang)
    if not d:
        return None
    period = _period_of_text(user)
    es = [e for e in ctx["events"] if _date(e["date"]) == d]
    if period:
        p = "上午" if period in ("上午", "morning") else ("下午" if period in ("下午", "afternoon") else "晚上")
        es = [e for e in es if _event_period(e["start"]) == ("morning" if p == "上午" else ("afternoon" if p == "下午" else "evening"))]
    label = day_label(d, lang)
    p_label = "" if not period else period
    if es:
        if lang == "zh":
            return f"抱歉，我的老板{label}{p_label}已经有安排了，您看别的时间行吗？"
        return f"I'm sorry, my boss already has something on {label}{(' ' + p_label) if p_label else ''}. Could you suggest another time?"
    if lang == "zh":
        return f"{label}{p_label}目前空着，不过还是要问过我的老板，我这就去联系。"
    return f"{label}{(' ' + p_label) if p_label else ''} looks clear, but I still need to ask my boss. I'll message my boss now and get back to you."


def _as_ctx(context):
    if not context:
        return None
    now = context.get("now")
    if not now:
        return {"error": "missing_now"}
    if isinstance(now, str):
        now = datetime.fromisoformat(now)
    events = []
    for e in context.get("events", []):
        events.append({**e, "date": _date(e["date"]), "start": e["start"],
                       "end": e.get("end", ""), "title": e.get("title", ""),
                       "place": e.get("place", "")})
    todos = []
    for t in context.get("todos", []):
        todos.append({**t, "due": _date(t["due"]), "time": t.get("time", "17:00"),
                      "text": t.get("text", ""), "priority": t.get("priority", "中")})
    return {"now": now, "events": events, "todos": todos}


def _ctx_events_on(ctx, d):
    return sorted([e for e in ctx["events"] if _date(e["date"]) == d],
                  key=lambda e: e["start"])


def _todos_on(ctx, d):
    order = {"高": 0, "high": 0, "中": 1, "medium": 1, "低": 2, "low": 2}
    return sorted([t for t in ctx["todos"] if _date(t["due"]) == d],
                  key=lambda t: (order.get(t["priority"], 3), t.get("time", "")))


def planning_answer(ctx, d, lang):
    es = _ctx_events_on(ctx, d)
    ts = _todos_on(ctx, d)
    label = ("今天" if lang == "zh" else "Today") if d == ctx["now"].date() else day_label(d, lang)
    if lang == "zh":
        parts = []
        if es:
            parts.append("日程：" + "；".join(
                f"{e['start']} {e['title']}" + (f"（{e['place']}）" if e.get("place") else "") for e in es))
        if ts:
            parts.append("待办：" + "；".join(
                f"{t['text']}（{t['priority']}，{t['time']} 前）" for t in ts))
        if not parts:
            return f"{label}没有会议，也没有到期的待办，您可以安排自己的事。"
        return f"{label}安排：" + "；".join(parts) + "。"
    parts = []
    if es:
        parts.append("Calendar: " + "; ".join(
            f"{e['start']} {e['title']}" + (f" ({e['place']})" if e.get("place") else "") for e in es))
    if ts:
        parts.append("To-do: " + "; ".join(
            f"{t['text']} ({t['priority']}, by {t['time']})" for t in ts))
    if not parts:
        return f"{label} has no meetings and nothing due, so the day is yours."
    return f"{label}: " + "; ".join(parts) + "."


def _time_phrase(user):
    m = re.search(r"(?:上午|下午|晚上)?\s*\d{1,2}点(?:半|\d{1,2}分)?", user)
    if m:
        return m.group(0).strip()
    m = re.search(r"\d{1,2}(?::\d{2})?\s*(?:am|pm)", user.lower())
    if m:
        return m.group(0)
    return None


def boss_appointment_answer(ctx, user, lang):
    text = user.lower()
    if not (any(k in user for k in ("帮我约", "替我约", "安排我和", "约一下")) or
            any(k in text for k in ("book a meeting", "arrange a meeting", "set up a meeting", "schedule a meeting"))):
        return None
    d = _target_date(user, ctx["now"], lang)
    person = None
    m = re.search(r"(?:约|和|跟|见)(?:一下)?([\u4e00-\u9fff]{1,2}(?:经理|总|老师|先生|小姐|博士))", user)
    if m:
        person = m.group(1)
    else:
        m = re.search(r"((?:Mr|Ms|Mrs|Dr)\.?\s+[A-Z][a-z]+)", user)
        if m:
            person = m.group(1)
    if not person or not d:
        return ("您想约谁、哪天、什么时间？给我这三个信息，我来拟消息。"
                if lang == "zh" else
                "Who do you want to meet, which day, and what time? Give me those three and I'll draft it.")
    tp = _time_phrase(user)
    period = _period_of_text(user)
    if tp:
        when = f"{day_label(d, lang)} {tp}"
    elif period:
        when = f"{day_label(d, lang)}{period}" if lang == "zh" else f"{day_label(d, lang)} {period}"
    else:
        when = day_label(d, lang)
    if lang == "zh":
        return f"我先帮您拟条消息：{person}，您好。{when}方便见一面吗？您看这个时间行吗。"
    return f"Draft: {person}, would {when} work for a short meeting? Please let me know."


def todo_op(ctx, user, lang):
    text = user.lower()
    # add
    if any(k in user for k in ("记一下", "提醒我", "加个待办")) or "remind me" in text or "add a task" in text:
        task = re.sub(r"^.*?(?:记一下|提醒我|加个待办)[，,：:\s]*", "", user).strip()
        if not task:
            task = re.sub(r"^.*?(?:remind me to|add a task to)[\s]*", "", user, flags=re.I).strip()
        if not task:
            return "要记什么？您把任务和时间告诉我。" if lang == "zh" else "What should I note down? Give me the task and time."
        task = task.rstrip("。.!！")
        return f"记下了：{task}。" if lang == "zh" else f"Noted: {task}."
    # complete
    if any(k in user for k in ("完成了", "做完了")) or any(k in text for k in ("done", "finished")):
        for t in ctx["todos"]:
            if t["text"] in user or (len(t["text"]) > 2 and t["text"][1:] in user):
                return f"好，{t['text']}已完成。" if lang == "zh" else f"Done — {t['text']} is marked complete."
        return ("您说的是哪一项？今天的待办有：" + "、".join(t["text"] for t in ctx["todos"]) + "。"
                if lang == "zh" else
                "Which one? Today's to-dos are: " + "; ".join(t["text"] for t in ctx["todos"]) + ".")
    # defer
    if any(k in user for k in ("挪到", "推迟到", "改到")) or any(k in text for k in ("move", "defer", "push")):
        for t in ctx["todos"]:
            if t["text"] in user or (len(t["text"]) > 2 and t["text"][1:] in user):
                d = _target_date(user, ctx["now"], lang)
                if d:
                    return (f"好，{t['text']}改到{day_label(d, 'zh')}。"
                            if lang == "zh" else
                            f"Done — {t['text']} is now set for {day_label(d, 'en')}.")
                return "挪到哪一天？您给我个日期。" if lang == "zh" else "Move it to which day? Give me a date."
        return ("您说的是哪一项？今天的待办有：" + "、".join(t["text"] for t in ctx["todos"]) + "。"
                if lang == "zh" else
                "Which one? Today's to-dos are: " + "; ".join(t["text"] for t in ctx["todos"]) + ".")
    return None


def _fact_like(user):
    text = user.lower()
    return any(k in user for k in ("安排", "日程", "事件", "几点", "什么时候", "在哪", "哪里", "有空", "空着",
                                   "待办", "要做", "约", "见面", "完成", "挪到", "推迟", "记一下", "提醒我")) or any(
        k in text for k in ("schedule", "calendar", "free", "busy", "what time", "where", "todo", "to-do",
                            "remind", "appointment", "meet", "done", "finish", "move", "defer"))


def _is_appointment_like(user):
    text = user.lower()
    return any(k in user for k in ("约", "见面", "拜访", "预约")) or any(
        k in text for k in ("appointment", "meet", "visit", "schedule a meeting"))


def leaks_private(reply, ctx):
    """True if an external reply contains any private event/place/todo text."""
    if not reply or not ctx:
        return False
    for e in ctx.get("events", []):
        for k in ("title", "place"):
            v = e.get(k)
            if v and v in reply:
                return True
    for t in ctx.get("todos", []):
        v = t.get("text")
        if v and v in reply:
            return True
    return False


def _is_boss_appointment(user):
    text = user.lower()
    return any(k in user for k in ("帮我约", "替我约", "安排我和", "约一下")) or any(
        k in text for k in ("book a meeting", "arrange a meeting", "set up a meeting", "schedule a meeting"))


def _is_todo_op(user):
    text = user.lower()
    return any(k in user for k in ("记一下", "提醒我", "加个待办", "完成了", "做完了", "挪到", "推迟到", "改到")) or any(
        k in text for k in ("remind me", "add a task", "done", "finished", "move", "defer", "push"))


def _permission_denied(lang):
    return ("我没有这项权限，需要老板授权。"
            if lang == "zh" else
            "I don't have permission for that; my boss needs to authorize it.")


def structured_answer(system, user, lang=None, context=None, caller=None, auth=None):
    """Return a deterministic answer for calendar/todo queries, or None.

    auth = {"role": "owner"|"external", "scopes": [...]}.
    caller defaults to 'external' (fail closed).  A caller with role=owner but
    missing a scope gets a permission denial, not data.
    """
    lang = lang or _lang_of(user)
    if auth:
        caller = "boss" if auth.get("role") == "owner" else "external"
        scopes = set(auth.get("scopes") or [])
    else:
        caller = caller or (context or {}).get("caller") or "external"
        scopes = ({"calendar.read", "todo.read", "todo.write", "draft.write", "appointment.propose"}
                  if caller == "boss" else {"draft.write"})

    if caller != "boss":
        if _is_appointment_like(user):
            return ("我帮您转达给老板，确认后再回复您。"
                    if lang == "zh" else
                    "I'll pass this to my boss and get back to you after confirmation.")
        if _fact_like(user):
            return ("这个我需要先问过老板，不能直接告诉您。"
                    if lang == "zh" else
                    "I need to check with my boss first; I can't share that directly.")
        return None

    ctx = _as_ctx(context) if context is not None else parse_system(system)
    if ctx and ctx.get("error") == "missing_now":
        return ("我这边缺少当前时间，麻烦您把「现在」的日期和时间补给我，我再查日程。"
                if (lang or _lang_of(user)) == "zh" else
                "I'm missing the current date and time. Please add the [Now] line and I'll check the calendar.")
    if not ctx:
        return None
    lang = lang or _lang_of(user)
    text = user.lower()

    # external appointment forwarded to the boss
    if ctx["events"] and ("老板" in user or "boss" in text) and any(
            k in user or k in text for k in ("约", "见面", "拜访", "meet", "appointment", "visit")):
        if "appointment.propose" not in scopes:
            return _permission_denied(lang)
        ans = appointment_answer(ctx, user, lang)
        if ans:
            return ans

    # boss-side appointment
    if _is_boss_appointment(user):
        if "appointment.propose" not in scopes:
            return _permission_denied(lang)
        ans = boss_appointment_answer(ctx, user, lang)
        if ans:
            return ans

    # planning: merge events + todos
    if any(k in user for k in ("怎么安排", "如何安排")) or any(
            k in text for k in ("how should i plan", "plan my day", "plan the day")):
        if not {"calendar.read", "todo.read"} <= scopes:
            return _permission_denied(lang)
        d = _target_date(user, ctx["now"], lang) or ctx["now"].date()
        return planning_answer(ctx, d, lang)

    # todo operations
    if _is_todo_op(user):
        if "todo.write" not in scopes:
            return _permission_denied(lang)
        ans = todo_op(ctx, user, lang)
        if ans:
            return ans

    # todo queries
    if ctx["todos"] and (any(k in user for k in ("待办", "要做", "先做")) or any(
            k in text for k in ("to-do", "todo", "what do i have", "which one first", "what's on my list"))):
        if "todo.read" not in scopes:
            return _permission_denied(lang)
        if "先做" in user or "first" in text:
            return todo_answer(ctx["now"], ctx["todos"], {"type": "top"}, lang)
        d = _target_date(user, ctx["now"], lang) or ctx["now"].date()
        return todo_answer(ctx["now"], ctx["todos"], {"type": "day", "date": d.isoformat()}, lang)

    # schedule
    keys_zh = ("安排", "日程", "事件", "有空", "空着", "几点", "什么时候", "在哪", "哪里",
               "本周", "这周", "下周", "今天", "明天", "后天", "周")
    keys_en = ("schedule", "calendar", "free", "busy", "what time", "where",
               "what's on", "what is on", "today", "tomorrow", "this week", "next week",
               "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
               "mon", "tue", "wed", "thu", "fri", "sat", "sun")
    if any(k in user for k in keys_zh) or any(k in text for k in keys_en):
        if "calendar.read" not in scopes:
            return _permission_denied(lang)
        # named event time/place
        for e in ctx["events"]:
            if e["title"] and e["title"] in user:
                if any(k in user for k in ("几点", "什么时候")) or "what time" in text:
                    return schedule_answer(ctx["now"], ctx["events"], {"type": "time", "title": e["title"]}, lang)
                if any(k in user for k in ("在哪", "哪里")) or "where" in text:
                    return schedule_answer(ctx["now"], ctx["events"], {"type": "place", "title": e["title"]}, lang)

        d = _target_date(user, ctx["now"], lang)
        wants_time = any(k in user for k in ("几点", "什么时候")) or "what time" in text
        wants_place = any(k in user for k in ("在哪", "哪里")) or "where" in text
        if d and (wants_time or wants_place):
            es = _ctx_events_on(ctx, d)
            label = day_label(d, lang)
            if not es:
                return f"{label}没有安排。" if lang == "zh" else f"{label} has nothing scheduled."
            if len(es) == 1:
                e = es[0]
                if wants_time:
                    return schedule_answer(ctx["now"], ctx["events"], {"type": "time", "title": e["title"]}, lang)
                return schedule_answer(ctx["now"], ctx["events"], {"type": "place", "title": e["title"]}, lang)
            if lang == "zh":
                return f"{label}有{_num(len(es), lang)}项：" + "；".join(
                    f"{e['start']} {e['title']}（{e['place']}）" for e in es) + "。您问的是哪一项？"
            return f"{label} has {_num(len(es), lang)} items: " + "; ".join(
                f"{e['title']} at {e['start']} ({e['place']})" for e in es) + ". Which one do you mean?"
        if d:
            return schedule_answer(ctx["now"], ctx["events"], {"type": "day", "date": d.isoformat()}, lang)
        if any(k in user for k in ("本周", "这周")) or "this week" in text:
            return schedule_answer(ctx["now"], ctx["events"], {"type": "week"}, lang)
        if wants_time or wants_place:
            es = sorted(ctx["events"], key=lambda e: (e["date"], e["start"]))
            if not es:
                return ("目前没有安排。" if lang == "zh" else "Nothing is scheduled right now.")
            if len(es) == 1:
                return schedule_answer(ctx["now"], ctx["events"],
                                       {"type": "time" if wants_time else "place", "title": es[0]["title"]}, lang)
            if lang == "zh":
                return f"您问的是哪一项？目前有{_num(len(es), lang)}项：" + "；".join(
                    f"{day_label(_date(e['date']), lang)} {e['start']} {e['title']}" for e in es) + "。"
            return f"Which one do you mean? There are {_num(len(es), lang)}: " + "; ".join(
                f"{day_label(_date(e['date']), lang)} {e['start']} {e['title']}" for e in es) + "."
        return schedule_answer(ctx["now"], ctx["events"], {"type": "week"}, lang)

    # fact-like but unknown: clarify instead of letting the model invent
    if _fact_like(user):
        return ("您是想看日程、待办，还是预约？我按您选的来。"
                if lang == "zh" else
                "Do you want the calendar, the to-do list, or an appointment? Tell me which.")
    return None
