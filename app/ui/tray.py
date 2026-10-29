# -*- coding: utf-8 -*-
"""System tray icon and menu for the pet app."""

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication


def _icon():
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QColor("#ffffff"))
    p.setPen(QPen(QColor("#999999"), 1))
    p.drawRoundedRect(4, 4, 24, 24, 4, 4)
    p.end()
    return QIcon(pm)


class TrayController(QObject):
    open_manager = Signal()
    open_chat = Signal()
    toggle_pet = Signal()
    toggle_voice = Signal()
    quit_app = Signal()

    def __init__(self, parent=None, app_name=None):
        super().__init__(parent)
        self.app_name = app_name or "YunPet"
        self.tray = QSystemTrayIcon(_icon(), parent)
        self.tray.setToolTip(self.app_name)
        menu = QMenu()
        a = menu.addAction("打开工作台")
        a.triggered.connect(self.open_manager)
        a = menu.addAction("聊天")
        a.triggered.connect(self.open_chat)
        a = menu.addAction("显示/隐藏桌宠")
        a.triggered.connect(self.toggle_pet)
        self.voice_action = menu.addAction("声音提示")
        self.voice_action.setCheckable(True)
        self.voice_action.setChecked(True)
        self.voice_action.toggled.connect(self.toggle_voice)
        menu.addSeparator()
        a = menu.addAction("退出")
        a.triggered.connect(self.quit_app)
        self.menu = menu
        self.tray.setContextMenu(menu)
        self.tray.show()

    def set_voice_checked(self, checked):
        self.voice_action.blockSignals(True)
        self.voice_action.setChecked(bool(checked))
        self.voice_action.blockSignals(False)

    def notify(self, title, body):
        self.tray.showMessage(title, body, QSystemTrayIcon.Information, 5000)


    def apply_language(self, lang):
        from app.core.i18n import tr_text
        for action in self.menu.actions():
            if action.text():
                action.setText(tr_text(action.text(), lang))
