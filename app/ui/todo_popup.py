# -*- coding: utf-8 -*-
"""Small auto-hiding card shown above the pet when it is clicked."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication


class TodoPopup(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setStyleSheet(
            "background:#ffffff;color:#333333;border:1px solid #d8d8d8;"
            "border-radius:8px;padding:10px 12px;font-size:13px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.resize(260, 80)

    def show_text(self, text, pet_geometry):
        self.label.setText(text)
        self.label.adjustSize()
        self.resize(min(320, max(220, self.label.width() + 24)),
                    max(60, self.label.height() + 20))
        screen = QApplication.screenAt(pet_geometry.center()) or QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None
        x = pet_geometry.center().x() - self.width() // 2
        y = pet_geometry.top() - self.height() - 8
        if geo is not None:
            x = max(geo.left() + 4, min(x, geo.right() - self.width() - 4))
            if y < geo.top() + 4:
                y = pet_geometry.bottom() + 8
        self.move(x, y)
        self.show()
        self.raise_()
        self._timer.start(6000)
