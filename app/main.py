# -*- coding: utf-8 -*-
"""Yun desktop pet entry point.

Run:
    python app\\main.py

The pet loads no model on startup.  Mail providers are intentionally empty;
plug Gmail/Outlook into app/mail_provider.py.
"""

import os
import sys
from datetime import datetime

from PySide6.QtCore import QTimer, Qt, QLockFile, QProcess
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(BASE)
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from app.core.storage import Storage
from app.core.config import Settings, APP_DATA, SKINS_DIR
from app.core.i18n import translate_tree
from app.ui.skin import style_sheet
from app.core.services import nearest_todo_text
from app.voice.manager import VoiceService
from app.model.manager import ModelManager
from app.ui.manager_window import ManagerWindow
from app.ui.chat_window import ChatWindow
from app.ui.pet_window import PetWindow
from app.ui.todo_popup import TodoPopup
from app.ui.tray import TrayController
from app.mail.sync import MailSync, notification_text, has_chinese
from app.mail.provider import build_provider


def default_pet_pos(screen):
    geo = screen.availableGeometry()
    return geo.right() - 104, geo.bottom() - 104


def in_quiet_hours(spec):
    spec = (spec or "").strip()
    if not spec or "-" not in spec:
        return False
    try:
        a, b = spec.split("-", 1)
        ah, am = map(int, a.split(":"))
        bh, bm = map(int, b.split(":"))
        now = datetime.now()
        cur = now.hour * 60 + now.minute
        start = ah * 60 + am
        end = bh * 60 + bm
        if start <= end:
            return start <= cur < end
        return cur >= start or cur < end
    except Exception:
        return False


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    os.makedirs(APP_DATA, exist_ok=True)
    os.makedirs(SKINS_DIR, exist_ok=True)
    settings = Settings()
    app.setStyleSheet(style_sheet(settings))
    lock = QLockFile(os.path.join(APP_DATA, "yunpet.lock"))
    lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        QMessageBox.warning(None, settings.get("app_name", "YunPet"),
                            "Already running. Close the existing pet first.")
        return

    storage = Storage()
    voice = VoiceService(settings)
    voice.start()
    model_client = ModelManager(settings)
    try:
        model_client.load()
        print(f"model: {model_client.status_text()}")
    except Exception as exc:
        print(f"model load failed: {exc}")
    manager = ManagerWindow(storage, settings, voice=voice, model_client=model_client)
    chat = ChatWindow(model_client, storage, voice=voice, settings=settings)

    x, y = settings.get("pet_x"), settings.get("pet_y")
    if x is None or y is None:
        screen = app.primaryScreen()
        x, y = default_pet_pos(screen)
    pet = PetWindow(x, y, settings)
    popup = TodoPopup()

    tray = TrayController(app_name=settings.get("app_name", "YunPet"))

    def show_todo():
        text = nearest_todo_text(storage, settings.get("language", "en"))
        popup.show_text(text, pet.geometry())
        voice.speak(text, source="pet", interrupt=True)

    def save_pos(px, py):
        settings.set("pet_x", px)
        settings.set("pet_y", py)

    def open_manager():
        manager.refresh_all()
        manager.show()
        manager.raise_()
        manager.activateWindow()

    def open_chat():
        chat.show()
        chat.raise_()
        chat.activateWindow()

    def toggle_pet():
        pet.setVisible(not pet.isVisible())

    def toggle_voice(on):
        settings.set("voice_enabled", bool(on))
        tray.set_voice_checked(bool(on))

    def restart_for_language():
        current = settings.get("language", "en")
        settings.set("language", "zh" if current == "en" else "en")
        voice.stop()
        storage.close()
        tray.tray.hide()
        lock.unlock()
        args = (sys.argv[1:] if getattr(sys, "frozen", False)
                else [os.path.abspath(__file__)] + sys.argv[1:])
        QProcess.startDetached(sys.executable, args)
        app.quit()

    def quit_app():
        voice.stop()
        storage.close()
        tray.tray.hide()
        lock.unlock()
        app.quit()

    pet.clicked.connect(show_todo)
    pet.moved.connect(save_pos)
    tray.open_manager.connect(open_manager)
    tray.open_chat.connect(open_chat)
    tray.toggle_pet.connect(toggle_pet)
    tray.toggle_voice.connect(toggle_voice)
    tray.quit_app.connect(quit_app)
    manager.language_requested.connect(restart_for_language)
    chat.language_requested.connect(restart_for_language)
    tray.set_voice_checked(bool(settings.get("voice_enabled", False)))
    if settings.get("language", "en") == "en":
        translate_tree(manager, "en")
        translate_tree(chat, "en")
        tray.apply_language("en")

    # Mail sync supports multiple accounts; none is configured by default.
    mail_sync = MailSync(storage, providers=[], settings=settings)
    mail_signature = None

    def ensure_mail_providers():
        nonlocal mail_signature
        accounts = settings.get("mail_accounts", [])
        if not isinstance(accounts, list):
            accounts = []
        sig = tuple((a.get("provider"), a.get("label"), a.get("client_id"))
                    for a in accounts if isinstance(a, dict))
        if sig == mail_signature:
            return
        providers = []
        for a in accounts:
            if not isinstance(a, dict):
                continue
            try:
                account_id = f"{a.get('provider', 'mail')}:{a.get('label', 'default')}"
                p = build_provider(a.get("provider", ""), account_id=account_id)
                p.connect({"client_id": a.get("client_id", "")})
                providers.append(p)
            except Exception:
                continue
        mail_sync.providers = providers
        mail_signature = sig

    def poll_mail():
        ensure_mail_providers()
        for row in mail_sync.poll():
            sender = row.get("sender", "")
            subject = row.get("subject", "")
            lang = "zh" if has_chinese(sender + subject) else "en"
            body = notification_text(sender, subject, lang,
                                     include_subject=bool(settings.get("include_subject_in_voice", True)))
            tray.notify("新邮件", body)
            if not in_quiet_hours(settings.get("quiet_hours", "")):
                voice.speak(body, source="mail")
            mail_sync.mark_notified(row["id"])
            popup.show_text(body, pet.geometry())

    mail_timer = QTimer()
    mail_timer.timeout.connect(poll_mail)
    mail_timer.start(max(15, int(settings.get("mail_poll_seconds", 60))) * 1000)

    pet.show()
    if "--smoke" in sys.argv:
        QTimer.singleShot(1200, quit_app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
