# -*- coding: utf-8 -*-
"""Context builder for the chat window.

Budget: 1024 total, reserve 240 for the reply; keep recent turns and an
extractive summary, never the whole history.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.config import PROJECT_DIR
from app.core.storage import Storage

OWNER_AUTH = {
    "role": "owner",
    "caller_id": "u_owner",
    "channel": "app",
    "scopes": ["calendar.read", "todo.read", "todo.write",
               "draft.write", "appointment.propose"],
}

MAX_PROMPT = 760
MAX_NEW = 120
MAX_TURNS = 6
MAX_SUMMARY = 3

FACT_KEYS_ZH = ("安排", "日程", "事件", "几点", "什么时候", "在哪", "哪里", "待办",
                "要做", "先做", "预约", "约", "完成", "挪到", "推迟")
FACT_KEYS_EN = ("schedule", "calendar", "what time", "where", "todo",
                "to-do", "appointment", "meeting", "remind", "done")
DATE_HINT_ZH = ("今天", "明天", "后天", "周", "下周", "本周")
DATE_HINT_EN = ("today", "tomorrow", "monday", "tuesday", "wednesday",
                "thursday", "friday", "saturday", "sunday")
CHAT_HINTS = ("忙吗", "忙不忙", "累吗", "吃了吗", "在吗", "怎么样", "你好",
              "谢谢", "晚安", "睡了吗", "干嘛", "最近")
DRAFT_HINTS_ZH = ("写", "草拟", "消息", "邮件", "回复", "起草", "措辞", "短信")
DRAFT_HINTS_EN = ("write", "draft", "message", "email", "reply", "compose", "wording")


@dataclass
class BuiltContext:
    system: str
    turns: list
    prompt_tokens: int
    kept: int
    omitted: int
    summary: str


def is_fact_query(user, state=None):
    text = user.lower()
    state = state or {}
    # A drafting request may mention a meeting/day but is not a calendar query.
    if any(k in user for k in DRAFT_HINTS_ZH) or any(k in text for k in DRAFT_HINTS_EN):
        return False
    if any(k in user for k in FACT_KEYS_ZH) or any(k in text for k in FACT_KEYS_EN):
        return True
    # "你今天忙吗" is chat, even if the previous turn was about the calendar.
    if any(k in user for k in CHAT_HINTS):
        return False
    if state.get("last_intent") in ("schedule", "todo"):
        if any(k in user for k in DATE_HINT_ZH) or any(k in text for k in DATE_HINT_EN):
            return True
    return False


def _event_dict(e):
    return {k: e.get(k, "") for k in ("date", "start", "end", "title", "place")}


def structured_context(storage: Storage, now=None):
    now = now or datetime.now()
    start = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    end = (now + timedelta(days=14)).strftime("%Y-%m-%d %H:%M")
    events = []
    for e in storage.list_events(start, end):
        start_at = e.get("start_at", "")
        day = start_at[:10]
        hm = start_at[11:16] if len(start_at) >= 16 else "09:00"
        end_at = e.get("end_at", "")
        end_hm = end_at[11:16] if len(end_at) >= 16 else hm
        events.append({"date": day, "start": hm, "end": end_hm,
                       "title": e.get("title", ""), "place": e.get("place", "")})
    todos = [{"due": t.get("due_at", "")[:10], "time": (t.get("due_at", "")[11:16] or "17:00"),
              "text": t.get("title", ""), "priority": t.get("priority", "中")}
             for t in storage.list_todos(done=False) if t.get("due_at")]
    return {"now": now.isoformat(sep=" "), "events": events, "todos": todos}


def try_structured(storage: Storage, user, state=None, language="zh"):
    """Return a deterministic reply for calendar/todo intents, else None."""
    if not is_fact_query(user, state):
        return None
    try:
        from app.chat.render import structured_answer
        return structured_answer(None, user, context=structured_context(storage),
                                 caller="boss", auth=OWNER_AUTH, lang=language)
    except Exception:
        return None


def _first_sentence(text, limit=40):
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    m = re.search(r"[。！？!?]", text)
    if m:
        text = text[:m.end()]
    return text[:limit]


def extract_summary(turns, old="", max_items=MAX_SUMMARY):
    items = []
    for t in turns:
        s = _first_sentence(t.get("content", ""))
        if s and s not in items:
            items.append(s)
        if len(items) >= max_items:
            break
    if old:
        items = [old] + [x for x in items if x != old]
    return "；".join(items[:max_items])


def infer_state(user, now=None, language="zh"):
    state = {}
    if any(k in user for k in ("待办", "要做", "先做", "完成", "挪到", "推迟")):
        state["last_intent"] = "todo"
    elif any(k in user for k in ("安排", "日程", "几点", "什么时候", "在哪", "预约", "约")):
        state["last_intent"] = "schedule"
    try:
        from app.chat.render import _target_date
        d = _target_date(user, now or datetime.now(), language)
        if d:
            state["last_date"] = d.isoformat()
    except Exception:
        pass
    return state


def build_context(model_client, storage: Storage, conversation_id, user,
                  history=None, now=None, language="zh"):
    now = now or datetime.now()
    state = storage.get_chat_state(conversation_id)
    fact = is_fact_query(user, state)

    from app.chat.render import render_system
    if fact:
        ctx = structured_context(storage, now)
        events = ctx["events"]
        todos = ctx["todos"]
        system = render_system(now, events, todos, {"address": "Boss" if language == "en" else "老板"}, language)
    else:
        system = render_system(now, [], [], None, language)

    history = history if history is not None else storage.list_chat_turns(conversation_id)
    history = [{"role": t["role"], "content": t["content"]} for t in history][-20:]

    summary = state.get("summary", "")
    recent = []
    omitted = 0
    # take newest turns first, then restore chronological order
    for t in reversed(history):
        recent.append(t)
        if len(recent) >= MAX_TURNS:
            break
    omitted = max(0, len(history) - len(recent))
    recent.reverse()

    # Extractive summary for turns that fall outside the window.
    if omitted:
        older = history[:omitted]
        summary = extract_summary(older, summary)

    def count(text):
        try:
            return model_client.count_tokens(text)
        except Exception:
            return max(1, len(text) // 2)

    def turn_tokens(turns):
        return sum(count(t["content"]) + 2 for t in turns) + 1

    current_tokens = count(user) + 2
    system_tokens = count(system) + 2
    # add summary to system if it fits
    if summary:
        candidate = system + ("\n[Earlier] " if language == "en" else "\n【之前聊过】") + summary
        if count(candidate) + 2 + current_tokens + turn_tokens(recent) <= MAX_PROMPT:
            system = candidate
            system_tokens = count(system) + 2

    while recent and system_tokens + current_tokens + turn_tokens(recent) > MAX_PROMPT:
        recent.pop(0)
        omitted += 1

    turns = [{"role": t["role"], "content": t["content"]} for t in recent]
    turns.append({"role": "user", "content": user})
    prompt_tokens = system_tokens + turn_tokens(turns)
    built = BuiltContext(system=system, turns=turns, prompt_tokens=prompt_tokens,
                         kept=len(recent), omitted=omitted, summary=summary)
    return built


def update_state_after(storage: Storage, conversation_id, user, answer="", language="zh"):
    state = infer_state(user, language=language)
    old = storage.get_chat_state(conversation_id)
    summary = old.get("summary", "")
    # Refresh the extractive summary from older turns occasionally.
    turns = storage.list_chat_turns(conversation_id)
    if len(turns) > MAX_TURNS:
        older = [{"content": t["content"]} for t in turns[:-MAX_TURNS]]
        summary = extract_summary(older, summary)
    storage.set_chat_state(conversation_id, summary=summary, **state)
