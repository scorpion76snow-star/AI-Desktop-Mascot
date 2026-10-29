# -*- coding: utf-8 -*-
"""Frameless white-square desktop pet with drag/click separation."""

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap

from app.ui.skin import pet_image
from PySide6.QtWidgets import QWidget, QApplication


class PetWindow(QWidget):
    clicked = Signal()
    moved = Signal(int, int)

    def __init__(self, x=None, y=None, settings=None):
        super().__init__()
        self.settings = settings
        image = pet_image(settings) if settings is not None else None
        self._image = QPixmap(image) if image else QPixmap()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(80, 80)
        self._press_global = None
        self._press_pos = None
        self._dragging = False
        self._moved = False
        self.move(x if x is not None else 100, y if y is not None else 100)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if not self._image.isNull():
            p.drawPixmap(self.rect(), self._image)
            return
        p.setBrush(QColor("#ffffff"))
        p.setPen(QPen(QColor("#d8d8d8"), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_pos = self.pos()
            self._dragging = True
            self._moved = False
            event.accept()

    def mouseMoveEvent(self, event):
        if not self._dragging or self._press_global is None:
            return
        delta = event.globalPosition().toPoint() - self._press_global
        if abs(delta.x()) > 5 or abs(delta.y()) > 5:
            self._moved = True
        if self._moved:
            target = self._press_pos + delta
            self.move(self._clamp(target))
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._dragging = False
        if self._moved:
            self.moved.emit(self.x(), self.y())
        else:
            self.clicked.emit()
        self._press_global = None
        self._press_pos = None
        event.accept()

    def _clamp(self, pos):
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        if screen is None:
            return pos
        geo = screen.availableGeometry()
        x = max(geo.left(), min(pos.x(), geo.right() - self.width()))
        y = max(geo.top(), min(pos.y(), geo.bottom() - self.height()))
        return QPoint(x, y)
