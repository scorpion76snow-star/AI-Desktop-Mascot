# -*- coding: utf-8 -*-
"""Calendar / to-do / notes / settings manager window."""

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QDateTime, QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QCalendarWidget, QListWidget, QListWidgetItem, QPushButton, QLabel,
    QLineEdit, QTextEdit, QComboBox, QCheckBox, QSlider, QSpinBox,
    QDialog, QDialogButtonBox, QMessageBox, QGroupBox, QDateTimeEdit,
)

from app.core.services import parse_dt, month_range, event_label, todo_label
from app.core.config import VOICES_DIR, SKINS_DIR
from app.core.i18n import translate_tree
from app.mail.provider import build_provider, MailProviderError


class EventDialog(QDialog):
    def __init__(self, parent=None, event=None, default_day=None, language="zh"):
        super().__init__(parent)
        self.setWindowTitle("编辑日程" if event else "新建日程")
        self.resize(380, 260)
        form = QFormLayout(self)
        self.title = QLineEdit(event.get("title", "") if event else "")
        self.start = QDateTimeEdit()
        self.start.setCalendarPopup(True)
        self.end = QDateTimeEdit()
        self.end.setCalendarPopup(True)
        self.place = QLineEdit(event.get("place", "") if event else "")
        self.note = QLineEdit(event.get("note", "") if event else "")

        base = datetime.now().replace(second=0, microsecond=0)
        if default_day is not None:
            base = datetime(default_day.year, default_day.month, default_day.day, 9, 0)
        if event:
            base = parse_dt(event.get("start_at")) or base
        self.start.setDateTime(QDateTime(base))
        self.end.setDateTime(QDateTime(base + timedelta(hours=1)))
        if event:
            end = parse_dt(event.get("end_at"))
            if end:
                self.end.setDateTime(QDateTime(end))

        form.addRow("标题", self.title)
        form.addRow("开始", self.start)
        form.addRow("结束", self.end)
        form.addRow("地点", self.place)
        form.addRow("备注", self.note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        translate_tree(self, language)

    def values(self):
        return {
            "title": self.title.text().strip(),
            "start_at": self.start.dateTime().toString("yyyy-MM-dd HH:mm"),
            "end_at": self.end.dateTime().toString("yyyy-MM-dd HH:mm"),
            "place": self.place.text().strip(),
            "note": self.note.text().strip(),
        }


class TodoDialog(QDialog):
    def __init__(self, parent=None, todo=None, language="zh"):
        super().__init__(parent)
        self.setWindowTitle("编辑待办" if todo else "新建待办")
        self.resize(380, 220)
        form = QFormLayout(self)
        self.title = QLineEdit(todo.get("title", "") if todo else "")
        self.due = QDateTimeEdit()
        self.due.setCalendarPopup(True)
        self.due.setDateTime(QDateTime(datetime.now().replace(second=0, microsecond=0)))
        self.priority = QComboBox()
        self.priority.addItems(["高", "中", "低"])
        if todo:
            due = parse_dt(todo.get("due_at"))
            if due:
                self.due.setDateTime(QDateTime(due))
            self.priority.setCurrentText(todo.get("priority", "中"))
        self.note = QLineEdit(todo.get("note", "") if todo else "")
        form.addRow("标题", self.title)
        form.addRow("截止", self.due)
        form.addRow("优先级", self.priority)
        form.addRow("备注", self.note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        translate_tree(self, language)

    def values(self):
        return {
            "title": self.title.text().strip(),
            "due_at": self.due.dateTime().toString("yyyy-MM-dd HH:mm"),
            "priority": {"High": "高", "Medium": "中", "Low": "低"}.get(
                self.priority.currentText(), self.priority.currentText()),
            "note": self.note.text().strip(),
        }


class ManagerWindow(QMainWindow):
    changed = Signal()
    language_requested = Signal()

    def __init__(self, storage, settings, voice=None, model_client=None, send_callback=None):
        super().__init__()
        self.storage = storage
        self.settings = settings
        self.voice = voice
        self.model_client = model_client
        self.send_callback = send_callback
        self.app_name = settings.get("app_name", "YunPet")
        self.language = settings.get("language", "en")
        self.setWindowTitle(self.app_name + (" · Workspace" if self.language == "en" else " · 工作台"))
        self.resize(820, 640)
        tabs = QTabWidget()
        tabs.addTab(self._calendar_tab(), "日历")
        tabs.addTab(self._todo_tab(), "待办")
        tabs.addTab(self._notes_tab(), "记事本")
        tabs.addTab(self._drafts_tab(), "待发送")
        tabs.addTab(self._settings_tab(), "设置")
        central = QWidget()
        outer = QVBoxLayout(central)
        top = QHBoxLayout()
        title = QLabel(self.app_name)
        title.setStyleSheet("font-size:16px;font-weight:600;")
        top.addWidget(title)
        top.addStretch(1)
        lang_btn = QPushButton("中文 / EN")
        lang_btn.clicked.connect(self.language_requested.emit)
        top.addWidget(lang_btn)
        outer.addLayout(top)
        outer.addWidget(tabs)
        self.setCentralWidget(central)
        self.refresh_all()

    # ---------------- calendar ----------------
    def _calendar_tab(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.selectionChanged.connect(self.refresh_calendar)
        lay.addWidget(self.calendar, 1)
        right = QVBoxLayout()
        self.event_list = QListWidget()
        right.addWidget(QLabel("选中日期的日程"))
        right.addWidget(self.event_list, 1)
        row = QHBoxLayout()
        for text, slot in (("新建", self.add_event), ("编辑", self.edit_event), ("删除", self.delete_event)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        right.addLayout(row)
        lay.addLayout(right, 1)
        return w

    def refresh_calendar(self):
        self.event_list.clear()
        d = self.calendar.selectedDate().toPython()
        start = datetime(d.year, d.month, d.day)
        end = start + timedelta(days=1)
        for e in self.storage.list_events(start.strftime("%Y-%m-%d %H:%M"),
                                          end.strftime("%Y-%m-%d %H:%M")):
            item = QListWidgetItem(event_label(e))
            item.setData(Qt.UserRole, e["id"])
            self.event_list.addItem(item)

    def add_event(self):
        d = self.calendar.selectedDate().toPython()
        dlg = EventDialog(self, default_day=d, language=self.language)
        if dlg.exec() and dlg.values()["title"]:
            v = dlg.values()
            self.storage.add_event(v["title"], v["start_at"], v["end_at"], v["place"], v["note"])
            self.refresh_calendar()
            self.changed.emit()

    def edit_event(self):
        item = self.event_list.currentItem()
        if not item:
            return
        eid = item.data(Qt.UserRole)
        event = next((e for e in self.storage.list_events() if e["id"] == eid), None)
        if not event:
            return
        dlg = EventDialog(self, event=event, language=self.language)
        if dlg.exec():
            v = dlg.values()
            self.storage.update_event(eid, v["title"], v["start_at"], v["end_at"], v["place"], v["note"])
            self.refresh_calendar()
            self.changed.emit()

    def delete_event(self):
        item = self.event_list.currentItem()
        if not item:
            return
        if QMessageBox.question(self, "删除", "确定删除这个日程？") == QMessageBox.Yes:
            self.storage.delete_event(item.data(Qt.UserRole))
            self.refresh_calendar()
            self.changed.emit()

    # ---------------- todos ----------------
    def _todo_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.todo_list = QListWidget()
        self.todo_list.itemDoubleClicked.connect(lambda _: self.edit_todo())
        lay.addWidget(self.todo_list, 1)
        row = QHBoxLayout()
        for text, slot in (("新建", self.add_todo), ("编辑", self.edit_todo),
                           ("完成/取消", self.toggle_todo), ("删除", self.delete_todo)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        lay.addLayout(row)
        return w

    def refresh_todos(self):
        self.todo_list.clear()
        for t in self.storage.list_todos():
            text = todo_label(t)
            if t["done"]:
                text = "✓ " + text
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, t["id"])
            item.setData(Qt.UserRole + 1, bool(t["done"]))
            self.todo_list.addItem(item)

    def add_todo(self):
        dlg = TodoDialog(self, language=self.language)
        if dlg.exec() and dlg.values()["title"]:
            v = dlg.values()
            self.storage.add_todo(v["title"], v["due_at"], v["priority"], v["note"])
            self.refresh_todos()
            self.changed.emit()

    def edit_todo(self):
        item = self.todo_list.currentItem()
        if not item:
            return
        tid = item.data(Qt.UserRole)
        todo = next((t for t in self.storage.list_todos() if t["id"] == tid), None)
        if not todo:
            return
        dlg = TodoDialog(self, todo=todo, language=self.language)
        if dlg.exec():
            v = dlg.values()
            self.storage.update_todo(tid, v["title"], v["due_at"], v["priority"], v["note"])
            self.refresh_todos()
            self.changed.emit()

    def toggle_todo(self):
        item = self.todo_list.currentItem()
        if not item:
            return
        self.storage.set_todo_done(item.data(Qt.UserRole), not item.data(Qt.UserRole + 1))
        self.refresh_todos()
        self.changed.emit()

    def delete_todo(self):
        item = self.todo_list.currentItem()
        if item and QMessageBox.question(self, "删除", "确定删除这个待办？") == QMessageBox.Yes:
            self.storage.delete_todo(item.data(Qt.UserRole))
            self.refresh_todos()
            self.changed.emit()

    # ---------------- notes ----------------
    def _notes_tab(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        left = QVBoxLayout()
        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self.load_note)
        left.addWidget(self.note_list, 1)
        row = QHBoxLayout()
        for text, slot in (("新建", self.new_note), ("删除", self.delete_note)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        left.addLayout(row)
        lay.addLayout(left, 1)
        right = QVBoxLayout()
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("标题")
        self.note_body = QTextEdit()
        right.addWidget(self.note_title)
        right.addWidget(self.note_body, 1)
        save = QPushButton("保存")
        save.clicked.connect(self.save_note)
        right.addWidget(save)
        lay.addLayout(right, 2)
        self._note_id = None
        self._note_timer = QTimer(self)
        self._note_timer.setSingleShot(True)
        self._note_timer.timeout.connect(self.save_note)
        self.note_body.textChanged.connect(lambda: self._note_timer.start(1000))
        return w

    def refresh_notes(self):
        current = self._note_id
        self.note_list.clear()
        for n in self.storage.list_notes():
            item = QListWidgetItem(n["title"] or "无标题")
            item.setData(Qt.UserRole, n["id"])
            self.note_list.addItem(item)
            if n["id"] == current:
                self.note_list.setCurrentItem(item)

    def load_note(self, item, _prev=None):
        if not item:
            return
        n = self.storage.get_note(item.data(Qt.UserRole))
        if n:
            self._note_id = n["id"]
            self.note_title.setText(n["title"])
            self.note_body.blockSignals(True)
            self.note_body.setPlainText(n["body"])
            self.note_body.blockSignals(False)

    def new_note(self):
        self._note_id = None
        self.note_title.clear()
        self.note_body.clear()
        self.note_title.setFocus()

    def save_note(self):
        title = self.note_title.text().strip()
        body = self.note_body.toPlainText()
        if not title and not body:
            return
        self._note_id = self.storage.save_note(self._note_id, title or "无标题", body)
        self.refresh_notes()

    def delete_note(self):
        item = self.note_list.currentItem()
        if item and QMessageBox.question(self, "删除", "确定删除这条笔记？") == QMessageBox.Yes:
            self.storage.delete_note(item.data(Qt.UserRole))
            self._note_id = None
            self.note_title.clear()
            self.note_body.clear()
            self.refresh_notes()

    # ---------------- drafts ----------------
    def _drafts_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.draft_list = QListWidget()
        lay.addWidget(QLabel("待发送草稿：只有你点“允许发送”才会交给邮件接口"))
        lay.addWidget(self.draft_list, 1)
        row = QHBoxLayout()
        refresh = QPushButton("刷新")
        refresh.clicked.connect(self.refresh_drafts)
        approve = QPushButton("允许发送")
        approve.clicked.connect(self.approve_draft)
        row.addWidget(refresh)
        row.addWidget(approve)
        lay.addLayout(row)
        return w

    def refresh_drafts(self):
        self.draft_list.clear()
        for d in self.storage.list_pending_drafts():
            item = QListWidgetItem(f"[{d['status']}] 给 {d['to_addr']} · {d['subject']}")
            item.setData(Qt.UserRole, d["id"])
            self.draft_list.addItem(item)

    def approve_draft(self):
        item = self.draft_list.currentItem()
        if not item:
            QMessageBox.information(self, "待发送", "先选一封草稿。")
            return
        did = item.data(Qt.UserRole)
        draft = next((d for d in self.storage.list_pending_drafts() if d["id"] == did), None)
        if not draft:
            return
        if QMessageBox.question(
                self, "允许发送",
                f"确认允许发送给 {draft['to_addr']}？\n主题：{draft['subject']}") != QMessageBox.Yes:
            return
        self.storage.approve_draft(did)
        if self.send_callback is None:
            QMessageBox.information(
                self, "已批准",
                "草稿已标记为允许发送。邮件接口接好后，由应用执行发送。")
        else:
            try:
                self.send_callback(draft)
                self.storage.mark_draft_sent(did)
            except Exception as exc:
                QMessageBox.warning(self, "发送失败", str(exc))
        self.refresh_drafts()

    # ---------------- settings ----------------
    def _settings_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        app_box = QGroupBox("App")
        af = QFormLayout(app_box)
        self.app_name_edit = QLineEdit(self.settings.get("app_name", "YunPet"))
        self.app_name_edit.editingFinished.connect(self.save_app_name)
        af.addRow("App name", self.app_name_edit)
        lang_hint = QLabel("语言切换按钮在窗口右上角，切换后应用会重启。")
        af.addRow(lang_hint)
        lay.addWidget(app_box)

        model_box = QGroupBox("模型")
        mf = QFormLayout(model_box)
        self.model_profile = QComboBox()
        self.model_profile.addItems(["local", "openai"])
        self.model_profile.setCurrentText(self.settings.get("model_profile", "local"))
        self.openai_base = QLineEdit(self.settings.get("openai_base_url", "https://api.openai.com/v1"))
        self.openai_model = QLineEdit(self.settings.get("openai_model", "gpt-4o-mini"))
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("API key（存入 Windows Credential Manager）")
        if self.model_client is not None:
            self.model_status = QLabel(self.model_client.status_text())
        else:
            self.model_status = QLabel("未启用")
        mf.addRow("当前模型", self.model_profile)
        mf.addRow("Base URL", self.openai_base)
        mf.addRow("OpenAI 模型", self.openai_model)
        mf.addRow("API Key", self.openai_key)
        mf.addRow(self.model_status)
        mrow = QHBoxLayout()
        model_save = QPushButton("保存模型")
        model_save.clicked.connect(self.save_model_settings)
        model_test = QPushButton("测试/加载")
        model_test.clicked.connect(self.load_model)
        mrow.addWidget(model_save)
        mrow.addWidget(model_test)
        mf.addRow(mrow)
        lay.addWidget(model_box)

        skin_box = QGroupBox("界面/形象")
        sf = QFormLayout(skin_box)
        self.skin_name = QLineEdit(self.settings.get("skin", "default"))
        self.skin_name.editingFinished.connect(lambda: self.settings.set("skin", self.skin_name.text().strip() or "default"))
        sf.addRow("皮肤", self.skin_name)
        sf.addRow(QLabel("把 pet.png / style.qss 放到 %APPDATA%\\YunPet\\skins\\<皮肤名>\\"))
        skin_open = QPushButton("打开皮肤目录")
        skin_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(SKINS_DIR)))
        sf.addRow(skin_open)
        lay.addWidget(skin_box)

        voice_box = QGroupBox("语音提醒")
        v = QFormLayout(voice_box)
        self.voice_enabled = QCheckBox("开启声音提示")
        self.voice_enabled.setChecked(bool(self.settings.get("voice_enabled", True)))
        self.voice_enabled.toggled.connect(lambda x: self.settings.set("voice_enabled", x))
        self.voice_chat = QCheckBox("聊天自动朗读")
        self.voice_chat.setChecked(bool(self.settings.get("voice_chat_enabled", True)))
        self.voice_chat.toggled.connect(lambda x: self.settings.set("voice_chat_enabled", x))
        self.voice_mail = QCheckBox("邮件提醒朗读")
        self.voice_mail.setChecked(bool(self.settings.get("voice_mail_enabled", True)))
        self.voice_mail.toggled.connect(lambda x: self.settings.set("voice_mail_enabled", x))
        self.voice_pet = QCheckBox("桌宠待办朗读")
        self.voice_pet.setChecked(bool(self.settings.get("voice_pet_enabled", False)))
        self.voice_pet.toggled.connect(lambda x: self.settings.set("voice_pet_enabled", x))
        self.voice_status = QLabel(self.voice.status() if self.voice else "未启用")
        self.voice_volume = QSlider(Qt.Horizontal)
        self.voice_volume.setRange(0, 100)
        self.voice_volume.setValue(int(float(self.settings.get("voice_volume", 0.9)) * 100))
        self.voice_volume.valueChanged.connect(
            lambda x: self.settings.set("voice_volume", round(x / 100, 2)))
        self.quiet = QLineEdit(self.settings.get("quiet_hours", ""))
        self.quiet.setPlaceholderText("例如 23:00-07:00，留空表示不启用")
        self.quiet.editingFinished.connect(lambda: self.settings.set("quiet_hours", self.quiet.text().strip()))
        v.addRow(self.voice_enabled)
        v.addRow(self.voice_chat)
        v.addRow(self.voice_mail)
        v.addRow(self.voice_pet)
        v.addRow("当前引擎", self.voice_status)
        v.addRow("音量", self.voice_volume)
        v.addRow("勿扰时段", self.quiet)
        test_row = QHBoxLayout()
        zh = QPushButton("试听中文")
        en = QPushButton("试听英文")
        zh.clicked.connect(lambda: self.voice and self.voice.speak("老板，这是中文语音测试。", source="test"))
        en.clicked.connect(lambda: self.voice and self.voice.speak("Boss, this is the English voice test.", source="test"))
        test_row.addWidget(zh)
        test_row.addWidget(en)
        v.addRow(test_row)
        voice_open = QPushButton("打开语音目录")
        voice_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(VOICES_DIR)))
        v.addRow(voice_open)
        lay.addWidget(voice_box)

        mail_box = QGroupBox("邮件账号（可多个）")
        m = QVBoxLayout(mail_box)
        self.mail_accounts = QListWidget()
        self.mail_accounts.currentRowChanged.connect(self._load_mail_account)
        m.addWidget(self.mail_accounts)
        form = QFormLayout()
        self.mail_provider = QComboBox()
        self.mail_provider.addItems(["Gmail", "Outlook"])
        self.mail_label = QLineEdit()
        self.mail_label.setPlaceholderText("账号备注，如 work")
        self.mail_client = QLineEdit()
        self.mail_client.setPlaceholderText("client_id / tenant_id")
        form.addRow("服务商", self.mail_provider)
        form.addRow("账号备注", self.mail_label)
        form.addRow("客户端 ID", self.mail_client)
        m.addLayout(form)
        row = QHBoxLayout()
        for text, slot in (("新增", self.new_mail_account),
                           ("保存", self.add_mail_account),
                           ("删除", self.delete_mail_account),
                           ("测试连接", self.test_mail)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        m.addLayout(row)
        self.refresh_mail_accounts()
        lay.addWidget(mail_box)

        lay.addStretch(1)
        return w

    def _mail_list(self):
        value = self.settings.get("mail_accounts", [])
        return list(value) if isinstance(value, list) else []

    def refresh_mail_accounts(self):
        self.mail_accounts.clear()
        for a in self._mail_list():
            label = a.get("label") or a.get("provider", "")
            client = a.get("client_id", "")
            item = QListWidgetItem(f"{label} · {a.get('provider', '')} · {client[:10]}")
            self.mail_accounts.addItem(item)
        if self.mail_accounts.count() and self.mail_accounts.currentRow() < 0:
            self.mail_accounts.setCurrentRow(0)

    def new_mail_account(self):
        self.mail_accounts.setCurrentRow(-1)
        self.mail_provider.setCurrentText("Gmail")
        self.mail_label.clear()
        self.mail_client.clear()

    def _load_mail_account(self, row):
        accounts = self._mail_list()
        if row < 0 or row >= len(accounts):
            return
        a = accounts[row]
        self.mail_provider.setCurrentText(a.get("provider", "gmail").capitalize())
        self.mail_label.setText(a.get("label", ""))
        self.mail_client.setText(a.get("client_id", ""))

    def add_mail_account(self):
        provider = self.mail_provider.currentText().lower()
        label = self.mail_label.text().strip() or provider
        client = self.mail_client.text().strip()
        accounts = self._mail_list()
        row = self.mail_accounts.currentRow()
        item = {"label": label, "provider": provider, "client_id": client}
        if 0 <= row < len(accounts):
            accounts[row] = item
        else:
            accounts.append(item)
        self.settings.set("mail_accounts", accounts)
        self.refresh_mail_accounts()

    def delete_mail_account(self):
        row = self.mail_accounts.currentRow()
        accounts = self._mail_list()
        if 0 <= row < len(accounts):
            accounts.pop(row)
            self.settings.set("mail_accounts", accounts)
            self.refresh_mail_accounts()
            self.mail_label.clear()
            self.mail_client.clear()

    def test_mail(self):
        row = self.mail_accounts.currentRow()
        accounts = self._mail_list()
        if not (0 <= row < len(accounts)):
            QMessageBox.information(self, "邮件", "先添加一个邮件账号。")
            return
        a = accounts[row]
        try:
            p = build_provider(a.get("provider", "gmail"),
                               account_id=f"{a.get('provider', 'gmail')}:{a.get('label', 'default')}")
            p.connect({"client_id": a.get("client_id", "")})
            QMessageBox.information(self, "邮件接口", "连接成功。")
        except MailProviderError as exc:
            QMessageBox.information(self, "邮件接口", str(exc))

    def save_app_name(self):
        name = self.app_name_edit.text().strip() or "YunPet"
        self.settings.set("app_name", name)
        self.setWindowTitle(name + (" · Workspace" if self.settings.get("language", "en") == "en" else " · 工作台"))

    def save_model_settings(self):
        self.settings.set("model_profile", self.model_profile.currentText())
        self.settings.set("openai_base_url", self.openai_base.text().strip())
        self.settings.set("openai_model", self.openai_model.text().strip())
        key = self.openai_key.text().strip()
        if key:
            try:
                import keyring
                keyring.set_password("YunPet", "YunPet/openai", key)
                self.openai_key.clear()
            except Exception as exc:
                QMessageBox.warning(self, "模型", f"保存 Key 失败：{exc}")
        if self.model_client is not None:
            self.model_client.backend = None
            self.model_client.profile = None
            self.model_status.setText("已保存，等待加载")
        QMessageBox.information(self, "模型", "模型设置已保存。")

    def load_model(self):
        if self.model_client is None:
            return
        try:
            self.model_client.load()
            self.model_status.setText(self.model_client.status_text())
        except Exception as exc:
            QMessageBox.warning(self, "模型", f"加载失败：{exc}")

    def refresh_all(self):
        self.refresh_calendar()
        self.refresh_todos()
        self.refresh_notes()
        self.refresh_drafts()
