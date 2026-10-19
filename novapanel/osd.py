"""Petite bulle d'information en bas de l'ecran, facon OSD de volume."""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget


class Osd(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.text, self.color = "", QColor("#5b8def")
        self.resize(320, 64)
        self.anim = QPropertyAnimation(self, b"windowOpacity", self)
        self.anim.setDuration(180)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.hide_timer = QTimer(self, singleShot=True, interval=1800)
        self.hide_timer.timeout.connect(self._fade_out)
        self._hide_connected = False

    def show_message(self, text, color="#5b8def"):
        self.text, self.color = text, QColor(color)
        w = QFontMetrics(self._font()).horizontalAdvance(text) + 64
        self.resize(max(200, w), 48)
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - self.width() // 2, scr.bottom() - self.height() - 70)
        self.anim.stop()
        if self._hide_connected:
            self.anim.finished.disconnect(self.hide)
            self._hide_connected = False
        if not self.isVisible():
            self.setWindowOpacity(0)
            self.show()
        self.anim.setStartValue(self.windowOpacity())
        self.anim.setEndValue(1.0)
        self.anim.start()
        self.update()
        self.hide_timer.start()

    def _fade_out(self):
        self.anim.stop()
        self.anim.setStartValue(self.windowOpacity())
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self._hide_connected = True
        self.anim.start()

    def _font(self):
        f = QFont(self.font())
        f.setPointSize(12)
        f.setWeight(QFont.DemiBold)
        return f

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.fillPath(path, QColor(24, 25, 28, 240))
        p.setPen(QColor(255, 255, 255, 28))
        p.drawPath(path)
        p.setPen(Qt.NoPen)
        p.setBrush(self.color)
        p.drawEllipse(20, r.center().y() - 4, 9, 9)
        p.setPen(QColor("#ededef"))
        p.setFont(self._font())
        p.drawText(r.adjusted(42, 0, -18, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text)
