# -*- coding: utf-8 -*-
"""Small domain helpers: calendar ranges, nearest todo, note helpers."""

from datetime import datetime, timedelta


def parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fmt_dt(value):
    dt = parse_dt(value)
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def month_range(dt):
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    return start, nxt


def day_range(dt):
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def nearest_todo_text(storage, lang="zh"):
    todo = storage.next_todo()
    if not todo:
        return "暂无待办，老板。" if lang == "zh" else "No to-dos, Boss."
    due = parse_dt(todo.get("due_at"))
    when = due.strftime("%m月%d日 %H:%M") if due and lang == "zh" else (
        due.strftime("%d %b %H:%M") if due else "未定"
    )
    if lang == "zh":
        return f"最近的待办：{todo['title']}，{when} 前，优先级{todo.get('priority', '中')}。"
    return f"Nearest to-do: {todo['title']}, due {when}, priority {todo.get('priority', 'medium')}."


def event_label(event, lang="zh"):
    start = parse_dt(event.get("start_at"))
    when = start.strftime("%m月%d日 %H:%M") if start and lang == "zh" else (
        start.strftime("%d %b %H:%M") if start else ""
    )
    return f"{when} {event.get('title', '')}"


def todo_label(todo, lang="zh"):
    due = parse_dt(todo.get("due_at"))
    when = due.strftime("%m月%d日 %H:%M") if due and lang == "zh" else (
        due.strftime("%d %b %H:%M") if due else "未定"
    )
    return f"{todo.get('title', '')}  ·  {when}  ·  {todo.get('priority', '中')}"
