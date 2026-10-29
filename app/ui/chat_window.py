# -*- coding: utf-8 -*-
"""Owner-only chat window with conversation history and a bounded context."""

import re

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel,
    QDialog, QListWidget, QListWidgetItem, QMessageBox,
)

from app.chat.context import build_context, try_structured, update_state_after
from app.chat.replies import emotional_reply
from app.chat.quality import validate_reply, fallback_reply
from app.core.i18n import translate_tree


def clean_for_speech(text):
    text = text or ""
    marker = "【AI助手回复：我是小云】"
    if text.startswith(marker):
        text = text[len(marker):].lstrip("\n")
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[*#>`_~]+", "", text)
    text = re.sub(r"^(消息|邮件|message|email|draft)[：:]\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 400:
        text = text[:400].rstrip("，。；;,. ") + "。详细内容在屏幕上。"
    return text



class ChatHistoryDialog(QDialog):
    """List conversations; open, delete one, or clear all."""

    def __init__(self, storage, current_id=None, parent=None, language="zh"):
        super().__init__(parent)
        self.storage = storage
        self.current_id = current_id
        self.chosen_id = None
        self.deleted_current = False
        self.cleared = False
        self.setWindowTitle("聊天记录")
        self.language = language
        self.resize(520, 420)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("选择一次对话打开；删除只影响聊天记录，不影响邮件/日历/待办。"))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self.open_selected())
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, slot in (("打开", self.open_selected),
                           ("删除选中", self.delete_selected),
                           ("清空全部", self.clear_all),
                           ("关闭", self.reject)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        lay.addLayout(row)
        translate_tree(self, self.language)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for c in self.storage.list_conversations():
            last = (c.get("last_content") or "").replace("\n", " ")[:36]
            text = (f"{c.get('title') or '新对话'}  ·  {c.get('updated_at', '')[:16]}"
                    f"  ·  {c.get('turn_count', 0)} 条  ·  {last}")
            item = QListWidgetItem(text)
            item.setData(0x0100, c["id"])
            self.list.addItem(item)
            if c["id"] == self.current_id:
                self.list.setCurrentItem(item)
        if not self.list.count():
            self.list.addItem("（暂无聊天记录）")

    def open_selected(self):
        item = self.list.currentItem()
        if not item or item.data(0x0100) is None:
            return
        self.chosen_id = item.data(0x0100)
        self.accept()

    def delete_selected(self):
        item = self.list.currentItem()
        if not item or item.data(0x0100) is None:
            return
        cid = item.data(0x0100)
        if QMessageBox.question(self, "删除聊天记录", "确定删除这次对话？") != QMessageBox.Yes:
            return
        self.storage.delete_conversation(cid)
        if cid == self.current_id:
            self.deleted_current = True
        self.refresh()

    def clear_all(self):
        if QMessageBox.question(self, "清空聊天记录", "确定删除全部聊天记录？此操作不可恢复。") != QMessageBox.Yes:
            return
        self.storage.delete_all_conversations()
        self.cleared = True
        self.deleted_current = True
        self.refresh()


class ChatWorker(QThread):
    done = Signal(str, str)

    def __init__(self, model_client, system, turns, parent=None):
        super().__init__(parent)
        self.model_client = model_client
        self.system = system
        self.turns = turns

    def run(self):
        try:
            text, _probs, gate = self.model_client.reply_messages(
                self.system, self.turns)
            self.done.emit(text or "", gate)
        except Exception as exc:
            self.done.emit("", f"ERROR: {exc}")


class ChatWindow(QWidget):
    language_requested = Signal()

    def __init__(self, model_client, storage, voice=None, settings=None):
        super().__init__()
        self.model_client = model_client
        self.storage = storage
        self.voice = voice
        self.settings = settings
        self.language = (settings.get("language", "en") if settings else "en")
        self.user_label = "Boss" if self.language == "en" else "老板"
        self.assistant_label = "Yun" if self.language == "en" else "小云"
        self.worker = None
        self._last_ctx = None
        self._pending_user = ""
        self._last_reply = ""
        self.conversation_id = None
        app_name = settings.get("app_name", "YunPet") if settings else "YunPet"
        self.setWindowTitle(app_name + (" · Chat" if self.language == "en" else " · 聊天"))
        self.resize(480, 560)

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.status = QLabel("")
        self.status.setStyleSheet("color:#666;")
        top.addWidget(self.status, 1)
        lang_btn = QPushButton("中文 / EN")
        lang_btn.clicked.connect(self.language_requested.emit)
        top.addWidget(lang_btn)
        speak_btn = QPushButton("朗读")
        speak_btn.clicked.connect(self.speak_last)
        top.addWidget(speak_btn)
        history_btn = QPushButton("历史")
        history_btn.clicked.connect(self.open_history)
        top.addWidget(history_btn)
        new_btn = QPushButton("新对话")
        new_btn.clicked.connect(self.new_conversation)
        top.addWidget(new_btn)
        lay.addLayout(top)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setStyleSheet(
            "background:#fafafa;border:1px solid #ddd;border-radius:6px;"
            "padding:8px;font-size:13px;"
        )
        lay.addWidget(self.transcript, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Say something to Yun…" if self.language == "en" else "和小云说点什么…")
        self.input.returnPressed.connect(self.send)
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)
        lay.addLayout(row)

        self._load_conversation()
        self.input.setFocus()

    def _speak(self, text, interrupt=True):
        clean = clean_for_speech(text)
        if not clean:
            return
        self._last_reply = clean
        if self.voice is not None:
            self.voice.speak(clean, source="chat", interrupt=interrupt)

    def speak_last(self):
        if self._last_reply and self.voice is not None:
            self.voice.speak(self._last_reply, source="chat", interrupt=True, force=True)

    def _load_conversation(self, conversation_id=None):
        if conversation_id is None:
            conv = self.storage.latest_conversation()
            if conv is None:
                self.conversation_id = self.storage.create_conversation()
            else:
                self.conversation_id = conv["id"]
        else:
            self.conversation_id = conversation_id
        self._last_ctx = None
        self._pending_user = ""
        self.transcript.clear()
        turns = self.storage.list_chat_turns(self.conversation_id, limit=20)
        for t in turns:
            prefix = self.user_label if t["role"] == "user" else self.assistant_label
            text = t["content"]
            if t["role"] == "assistant":
                marker = "【AI助手回复：我是小云】"
                if text.startswith(marker):
                    text = text[len(marker):].lstrip("\n")
            self.transcript.append(f"{prefix}: {text}" if self.language == "en" else f"{prefix}：{text}")
        if not turns:
            self.transcript.append("Yun: I'm here, Boss." if self.language == "en" else "小云：我在这儿，老板。")
        assistants = [t["content"] for t in turns if t["role"] == "assistant"]
        self._last_reply = clean_for_speech(assistants[-1]) if assistants else ""
        self.status.setText(f"Context: {min(len(turns), 6)} turns · new chat" if self.language == "en" else f"上下文：{min(len(turns), 6)} 轮 · 新对话可用")
        self.input.setFocus()

    def open_history(self):
        dlg = ChatHistoryDialog(self.storage, self.conversation_id, self, self.language)
        dlg.exec()
        if dlg.chosen_id is not None:
            self._load_conversation(dlg.chosen_id)
        elif dlg.cleared or dlg.deleted_current:
            self._load_conversation()

    def new_conversation(self):
        self.conversation_id = self.storage.create_conversation()
        self._last_ctx = None
        self._pending_user = ""
        self._last_reply = ""
        self.transcript.clear()
        self.transcript.append("Yun: New conversation started, Boss." if self.language == "en" else "小云：新对话开始了，老板。")
        self.status.setText("Context: 0 turns" if self.language == "en" else "上下文：0 轮")
        self.input.setFocus()

    def send(self):
        text = self.input.text().strip()
        if not text or self.worker is not None:
            return
        self.input.clear()
        self.transcript.append(f"{self.user_label}: {text}" if self.language == "en" else f"老板：{text}")

        # High-risk routing is deterministic even if the gate head slips.
        try:
            from app.chat.guard import classify
            forced = classify(text)
        except Exception:
            forced = None
        if forced == 1:
            self.storage.add_chat_turn(self.conversation_id, "user", text)
            self.transcript.append("Yun: [Handoff] I won't handle this automatically; please confirm." if self.language == "en" else "小云：[转人工] 这条我不自动处理，等老板确认。")
            self.status.setText("Context: rule handoff (model not called)" if self.language == "en" else "上下文：规则转人工（未调用模型）")
            return
        if forced == 2:
            self.storage.add_chat_turn(self.conversation_id, "user", text)
            self.transcript.append("Yun: [Ignored] This is logged only; no reply." if self.language == "en" else "小云：[忽略] 这条只汇总，不回复。")
            self.status.setText("Context: rule ignored (model not called)" if self.language == "en" else "上下文：规则忽略（未调用模型）")
            return

        # High-risk emotional / affection turns are handled by templates.
        emotional = emotional_reply(text, self.language)
        if emotional:
            self.storage.add_chat_turn(self.conversation_id, "user", text)
            self.storage.add_chat_turn(self.conversation_id, "assistant", emotional)
            update_state_after(self.storage, self.conversation_id, text, emotional, language=self.language)
            self.transcript.append(f"{self.assistant_label}: {emotional}" if self.language == "en" else f"小云：{emotional}")
            self._speak(emotional)
            self.status.setText("Context: deterministic template (model not called)" if self.language == "en" else "上下文：确定性模板（未调用模型）")
            return

        # Deterministic calendar/todo intent: no model, no fact rewriting.
        answer = try_structured(self.storage, text,
                                self.storage.get_chat_state(self.conversation_id), language=self.language)
        if answer:
            self.storage.add_chat_turn(self.conversation_id, "user", text)
            self.storage.add_chat_turn(self.conversation_id, "assistant", answer)
            update_state_after(self.storage, self.conversation_id, text, answer, language=self.language)
            self.transcript.append(f"{self.assistant_label}: {answer}" if self.language == "en" else f"小云：{answer}")
            self._speak(answer)
            self.status.setText("Context: structured calendar/todo (model not called)" if self.language == "en" else "上下文：结构化日程/待办（未调用模型）")
            return

        history = self.storage.list_chat_turns(self.conversation_id)
        try:
            built = build_context(self.model_client, self.storage,
                                  self.conversation_id, text, history=history, language=self.language)
        except Exception as exc:
            self.transcript.append(f"系统：上下文构建失败：{exc}")
            return
        self._last_ctx = built
        self._pending_user = text
        self.storage.add_chat_turn(
            self.conversation_id, "user", text,
            token_count=self.model_client.count_tokens(text))
        self._set_busy(True)
        self.status.setText(
            f"上下文：{built.kept} 轮"
            f"{'（省略 ' + str(built.omitted) + ' 轮）' if built.omitted else ''}"
            f"{' + 摘要' if built.summary else ''}"
            f" · 约 {built.prompt_tokens} tokens"
        )
        self.worker = ChatWorker(self.model_client, built.system, built.turns, self)
        self.worker.done.connect(self.on_done)
        self.worker.finished.connect(self._clear_worker)
        self.worker.start()

    def _set_busy(self, busy):
        self.input.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)
        if not busy:
            self.input.setFocus()

    def _clear_worker(self):
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        self._set_busy(False)

    def on_done(self, text, gate):
        blocked = False
        if gate.startswith("ERROR"):
            self.transcript.append(f"系统：{gate}")
        elif not text:
            self.transcript.append(f"小云：[{gate}] 这条不自动回复，等老板处理。")
        else:
            marker = "【AI助手回复：我是小云】"
            if text.startswith(marker):
                text = text[len(marker):].lstrip("\n")
            turns = self.storage.list_chat_turns(self.conversation_id)
            previous = [t["content"] for t in turns if t["role"] == "assistant"][-3:]
            ok, reason = validate_reply(self._pending_user, text, previous, language=self.language)
            if not ok:
                blocked = True
                text = fallback_reply(self._pending_user, self.language)
            # Store only the validated text (or the safe fallback). Bad model
            # output never enters chat_turns, so it cannot poison the next turn.
            self.storage.add_chat_turn(
                self.conversation_id, "assistant", text,
                token_count=self.model_client.count_tokens(text))
            if ok:
                update_state_after(self.storage, self.conversation_id,
                                   self._pending_user, text, language=self.language)
            self.transcript.append(f"{self.assistant_label}: {text}" if self.language == "en" else f"小云：{text}")
            self._speak(text)
        self._pending_user = ""
        ctx = ""
        if self._last_ctx is not None:
            if self.language == "en":
                ctx = (f"Context: {self._last_ctx.kept} turns"
                       f"{' (omitted ' + str(self._last_ctx.omitted) + ')' if self._last_ctx.omitted else ''}"
                       f"{' + summary' if self._last_ctx.summary else ''}"
                       f" · {self._last_ctx.prompt_tokens} tokens · ")
            else:
                ctx = (f"上下文：{self._last_ctx.kept} 轮"
                       f"{'（省略 ' + str(self._last_ctx.omitted) + ' 轮）' if self._last_ctx.omitted else ''}"
                       f"{' + 摘要' if self._last_ctx.summary else ''}"
                       f" · {self._last_ctx.prompt_tokens} tokens · ")
        suffix = (" · low-quality reply blocked" if self.language == "en" else " · 已拦截低质量回复") if blocked else ""
        self.status.setText(ctx + (f"Model: {self.model_client.status_text()}{suffix}" if self.language == "en" else f"模型：{self.model_client.status_text()}{suffix}"))
