"""NovaPanel : remplace SteelSeries GG pour l'Arctis Nova Pro Wireless.

Interface web (Qt WebEngine) reliee au programme par QWebChannel.
"""
import base64
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon

from . import __version__, config, updates, i18n, oled, system
from .autoeq import AutoEq
from .device import Base, battery_percent
from .i18n import t
from .media import NowPlaying
from .osd import Osd
from .screen import Compositor, overlay_text

gg = None
if sys.platform == "win32":
    from . import gg

HERE = Path(__file__).resolve().parent
UI = HERE / "ui" / "index.html"
ICON = HERE / "assets" / "icon.png"
ANC_COLORS = ["#8a8d96", "#3fb6a8", "#5b8def"]
PAGES = ["clock", "music", "pc", "rotate"]
EQ_BASE = ["Flat", "Bass Boost", "Focus", "Smiley"]
OK, DANGER, MUTED = "#3fb950", "#f85149", "#8a8d96"


def tray_icon(state):
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    online = state.get("connected") and state.get("headset") in ("online", "charging")
    level = state.get("battery", 0) if online else 0
    frame = QColor("#e6e7ea") if online else QColor("#6e7178")
    if not online:
        color = QColor("#6e7178")
    elif level <= 2:
        color = QColor(DANGER)
    elif state.get("headset") == "charging":
        color = QColor(OK)
    else:
        color = QColor("#e6e7ea")
    p.setPen(Qt.NoPen)
    p.setBrush(frame)
    p.drawRoundedRect(23, 3, 18, 6, 2, 2)
    pen = p.pen()
    pen.setColor(frame)
    pen.setWidth(5)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(13, 9, 38, 52, 7, 7)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    h = int(42 * level / 8)
    if h:
        p.drawRoundedRect(18, 56 - h, 28, h, 3, 3)
    if state.get("mic_muted") and online:
        p.setBrush(QColor(DANGER))
        p.drawEllipse(40, 40, 22, 22)
        pen = p.pen()
        pen.setColor(QColor("white"))
        pen.setWidth(3)
        p.setPen(pen)
        p.drawLine(46, 46, 56, 56)
        p.drawLine(56, 46, 46, 56)
    p.end()
    return QIcon(pm)


class Api(QObject):
    """Ce que l'interface web peut appeler, et les signaux qu'elle ecoute."""
    stateChanged = Signal(str)
    configChanged = Signal(str)
    frame = Signal(str, str)
    forcedBlack = Signal(bool)
    notify = Signal(str)
    updateAvailable = Signal(str)

    def __init__(self, app):
        super().__init__()
        self.app = app

    @Slot(result=str)
    def getState(self):
        return json.dumps(self.app.state)

    @Slot(result=str)
    def getConfig(self):
        return json.dumps(self.app.cfg)

    @Slot(result=str)
    def getStrings(self):
        return json.dumps({"lang": i18n.lang, **i18n.STRINGS[i18n.lang]})

    @Slot(result=str)
    def getMeta(self):
        return json.dumps({"version": __version__, "platform": sys.platform,
                           "autostart": system.autostart_enabled(), "hotkeys": system.HOTKEYS,
                           "media": self.app.media.available, "gg": self.app.gg_status(),
                           "forced_black": self.app.comp.forced_black, "update": self.app.update_info,
                           "firmware": self.app.base.state.get("firmware", "")})

    @Slot(str, int)
    def set(self, name, value):
        self.app.send(name, value)

    @Slot(str)
    def setEq(self, gains_json):
        self.app.send_eq(json.loads(gains_json))

    @Slot(str, str)
    def setCfg(self, key, value_json):
        self.app.set_cfg(key, json.loads(value_json))

    @Slot()
    def resendFrame(self):
        self.app._last_frame = None

    @Slot()
    def refresh(self):
        self.app.io.submit(self.app.base.refresh)

    @Slot()
    def toggleBlack(self):
        self.app.force_black(not self.app.comp.forced_black)

    @Slot(bool)
    def setAutostart(self, on):
        system.set_autostart(on)

    @Slot(result=str)
    def toggleGG(self):
        return json.dumps(self.app.toggle_gg())

    @Slot(result=str)
    def runningApps(self):
        return json.dumps(system.window_apps())

    @Slot(str)
    def openUrl(self, url):
        if url.startswith("https://"):
            QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def startDrag(self):
        self.app.window.windowHandle().startSystemMove()

    @Slot()
    def minimize(self):
        self.app.window.showMinimized()

    @Slot()
    def hide(self):
        self.app.window.hide()


class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        if "--debug" in sys.argv:
            print(f"[js] {source}:{line} {message}")


class Window(QMainWindow):
    def __init__(self, api):
        super().__init__()
        self.setWindowTitle("NovaPanel")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self.setStyleSheet("background:#111214;")
        self.view = QWebEngineView(self)
        page = Page(self.view)
        s = page.settings()
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        page.setBackgroundColor(QColor("#111214"))
        self.view.setPage(page)
        self.channel = QWebChannel(page)
        self.channel.registerObject("api", api)
        page.setWebChannel(self.channel)
        self.view.load(QUrl.fromLocalFile(str(UI)))
        self.view.setContextMenuPolicy(Qt.NoContextMenu)
        self.setCentralWidget(self.view)
        self._styled = False

    def showEvent(self, e):
        super().showEvent(e)
        if not self._styled:
            self._styled = True
            system.style_window(self)

    def closeEvent(self, e):
        e.ignore()
        self.hide()


class Bridge(QObject):
    """Ramene sur le thread Qt ce qui arrive des threads USB, ecran et systeme."""
    state = Signal(dict)
    update = Signal(object)
    sysevent = Signal(str)
    frame = Signal(str, str)


class NovaPanel:
    def __init__(self, qapp, show_window):
        self.qapp = qapp
        self.cfg = config.load()
        self.state = {}
        self.bridge = Bridge()
        self.io = ThreadPoolExecutor(1)  # ecritures USB lancees depuis l'interface, dans l'ordre
        self.base = Base(on_change=self.bridge.state.emit, debug="--debug" in sys.argv)
        self.media = NowPlaying()
        self.comp = Compositor(self.base, self.cfg, on_frame=self._on_frame, media=self.media)
        self.watcher = system.SystemWatcher(self._on_sys_event)
        self.autoeq = AutoEq(self._apply_eq_target, ignored=system.SHELL_APPS)
        self.osd = Osd()
        self.api = Api(self)
        self.window = Window(self.api)
        self._last_frame = None
        self._low_notified = False

        self.tray = QSystemTrayIcon(tray_icon({}))
        self.tray.setToolTip("NovaPanel")
        self.tray.activated.connect(self._tray_click)
        self.menu = self._menu()
        self.tray.setContextMenu(self.menu)
        self.tray.show()

        self.bridge.state.connect(self._on_state)
        self.bridge.sysevent.connect(self._on_sys_event_ui)
        self.bridge.frame.connect(self.api.frame)
        self.base.start()
        self.media.start()
        self.comp.start()
        self.watcher.set_hotkeys(self.cfg["hotkeys"])
        self.watcher.start()

        # la base ne signale pas tout (micro coupe, batterie) : on relit l'etat regulierement
        self.poll = QTimer(interval=2000)
        self.poll.timeout.connect(lambda: self.io.submit(self.base.write, 0x06, 0xB0))
        self.poll.start()
        self.rules_timer = QTimer(interval=1500)
        self.rules_timer.timeout.connect(self._check_rules)
        self.rules_timer.start()
        self.update_info = None
        self.bridge.update.connect(self._on_update)
        self.tray.messageClicked.connect(self._open_update)
        self.update_timer = QTimer(interval=24 * 3600 * 1000)
        self.update_timer.timeout.connect(self._check_updates)
        self.update_timer.start()
        QTimer.singleShot(15000, self._check_updates)

        if show_window:
            self.show_window()

    def _menu(self):
        m = QMenu()
        self.open_action = m.addAction("", self.show_window)
        m.addSeparator()
        self.anc_actions = []
        for i in range(3):
            a = QAction(m, checkable=True)
            a.triggered.connect(lambda _c, i=i: self.send("anc", i))
            m.addAction(a)
            self.anc_actions.append(a)
        m.addSeparator()
        self.black_action = QAction(m, checkable=True)
        self.black_action.triggered.connect(lambda on: self.force_black(on))
        m.addAction(self.black_action)
        m.addSeparator()
        self.quit_action = m.addAction("", self.quit)
        self._translate_menu()
        return m

    def _translate_menu(self):
        self.open_action.setText(t("open"))
        for a, label in zip(self.anc_actions, t("anc_names")):
            a.setText(label)
        self.black_action.setText(t("base_screen_off"))
        self.quit_action.setText(t("quit"))

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.Trigger and sys.platform != "darwin":
            if self.window.isVisible() and not self.window.isMinimized():
                self.window.hide()
            else:
                self.show_window()

    def show_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def send(self, name, value):
        self.io.submit(self.base.set, name, value)

    def send_eq(self, gains):
        self.io.submit(self.base.set_eq, gains)

    def set_cfg(self, key, value):
        self.cfg[key] = value
        config.save(self.cfg)
        if key == "hotkeys":
            self.watcher.set_hotkeys(value)
        if key == "language":
            i18n.set_language(value)
            self._translate_menu()
            self._update_tooltip()
        self.comp.reset()
        self.api.configChanged.emit(json.dumps(self.cfg))

    def force_black(self, on):
        self.comp.forced_black = on
        self.black_action.setChecked(on)
        self.api.forcedBlack.emit(on)

    def show_osd(self, text, color="#5b8def"):
        if self.cfg["osd"]:
            self.osd.show_message(text, color)

    def _current_eq_target(self):
        p = self.state.get("eq_preset")
        if p is None:
            return None
        if p < 4:
            return f"base:{p}"
        return "curve:" + json.dumps(self.state.get("eq", [0] * 10))

    def _apply_eq_target(self, target, app):
        kind, _, val = target.partition(":")
        if kind == "base":
            self.send("eq_preset", int(val))
            label = EQ_BASE[int(val)]
        elif kind == "user" and val in self.cfg["eq_presets"]:
            self.send_eq(self.cfg["eq_presets"][val])
            label = val
        elif kind == "curve":
            self.send_eq(json.loads(val))
            label = t("prev_curve")
        else:
            return
        self.show_osd(t("osd_eq", label=label) + (f" ({app})" if app else ""))

    def _check_rules(self):
        if self.cfg["eq_rules"] and self.state.get("connected"):
            self.autoeq.check(self.cfg["eq_rules"], self._current_eq_target(), system.foreground_app())

    def _on_frame(self, img, info):
        # thread de l'ecran : n'envoie a l'interface que si l'image a change
        raw = img.tobytes()
        key = (raw, info)
        if key != self._last_frame and self.window.isVisible():
            self._last_frame = key
            self.bridge.frame.emit(base64.b64encode(raw).decode(), info)

    def _on_state(self, s):
        old, self.state = self.state, s
        self.comp.update_state(s)
        self.tray.setIcon(tray_icon(s))
        for i, a in enumerate(self.anc_actions):
            a.setChecked(s.get("anc") == i)
        self.api.stateChanged.emit(json.dumps(s))
        self._last_frame = None

        if s.get("connected") and not old.get("connected"):
            if not (gg and gg.running()):
                self.io.submit(self.base.hardware_volume_mode)
            self.comp.reset()

        self._update_tooltip()

        # bulle a l'ecran pour les changements faits depuis le casque
        if old.get("connected") and s.get("headset") == "online":
            if "mic_muted" in old and s.get("mic_muted") != old.get("mic_muted") and self.cfg["osd_mic"]:
                self.show_osd(t("info_mic"), DANGER) if s["mic_muted"] else self.show_osd(t("mic_on"), OK)
            if "anc" in old and s.get("anc") != old.get("anc") and s["anc"] < 3:
                self.show_osd(t("anc_names")[s["anc"]], ANC_COLORS[s["anc"]])
        if old.get("headset") != s.get("headset") and old.get("connected") and s.get("connected"):
            if s.get("headset") == "online" and old.get("headset") == "offline":
                self.show_osd(t("headset_back", p=battery_percent(s.get("battery", 0))), OK)
            elif s.get("headset") == "offline" and old.get("headset") == "online":
                self.show_osd(t("headset_off"), MUTED)

        lvl, low = s.get("battery"), self.cfg["low_battery_level"]
        if s.get("headset") == "online" and lvl is not None and low > 0:
            if lvl <= low and not self._low_notified:
                self._low_notified = True
                self.tray.showMessage(t("low_title"), t("low_body", p=battery_percent(lvl)),
                                      QSystemTrayIcon.Warning, 8000)
                self.comp.toast(lambda: overlay_text(t("oled_low"), t("oled_low_line", p=battery_percent(lvl))), 5)
            elif lvl > low:
                self._low_notified = False
        if (self.cfg["notify_spare_full"] and old.get("spare_battery") is not None
                and old["spare_battery"] < 8 and s.get("spare_battery") == 8):
            self.tray.showMessage(t("spare_title"), t("spare_body"),
                                  QSystemTrayIcon.Information, 6000)

    def _update_tooltip(self):
        s, tip = self.state, "NovaPanel"
        if s.get("headset") in ("online", "charging"):
            tip += " — " + t("tip_battery", p=battery_percent(s.get("battery", 0)))
            if s.get("mic_muted"):
                tip += " — " + t("info_mic").lower()
        elif s.get("connected"):
            tip += " — " + t("headset_off").lower()
        else:
            tip += " — " + t("base_missing").lower()
        self.tray.setToolTip(tip)

    def _on_sys_event(self, ev):
        # appele hors du thread Qt : veille et extinction doivent eteindre l'ecran tout de suite
        if (ev == "suspend" and self.cfg["black_on_sleep"]) or (ev == "shutdown" and self.cfg["black_on_shutdown"]):
            self.comp.suspended = True
            self.comp.black_now()
        self.bridge.sysevent.emit(ev)

    def _on_sys_event_ui(self, ev):
        if ev == "lock":
            self.comp.locked = True
        elif ev == "unlock":
            self.comp.locked = False
        elif ev == "resume":
            self.comp.suspended = False
            self.comp.reset()
            self.io.submit(self.base.refresh)
        elif ev == "hotkey:anc_cycle":
            nxt = (self.state.get("anc", 0) + 1) % 3
            self.send("anc", nxt)
            self.show_osd(t("anc_names")[nxt], ANC_COLORS[nxt])
        elif ev == "hotkey:screen_black":
            self.force_black(not self.comp.forced_black)
            self.show_osd(t("base_screen_off") if self.comp.forced_black else t("base_screen_on"))
        elif ev == "hotkey:screen_page":
            if self.cfg["screen_mode"] != "custom":
                self.set_cfg("screen_mode", "custom")
                page = self.cfg["screen_page"]
            else:
                page = PAGES[(PAGES.index(self.cfg["screen_page"]) + 1) % len(PAGES)]
                self.set_cfg("screen_page", page)
            self.show_osd(t("osd_page", page=t("page_" + page)))
        elif ev.startswith("hotkey_failed:"):
            self.api.notify.emit(t("hk_failed", k=ev.split(":", 1)[1]))

    def _check_updates(self):
        if self.cfg["check_updates"]:
            updates.check_async(self.bridge.update.emit)

    def _on_update(self, res):
        if not res or res == self.update_info:
            return
        self.update_info = res
        self.tray.showMessage(t("update_title", version=res[0]), t("update_body"), QSystemTrayIcon.Information, 10000)
        self.api.updateAvailable.emit(json.dumps(res))

    def _open_update(self):
        if self.update_info:
            QDesktopServices.openUrl(QUrl(self.update_info[1]))

    def gg_status(self):
        if not gg:
            return None
        running, auto = gg.running(), gg.autostart_enabled()
        if running:
            status = t("gg_running")
        elif auto:
            status = t("gg_auto")
        else:
            status = t("gg_off")
        button = t("gg_stop") if (running or auto) else t("gg_enable")
        return {"running": running, "autostart": auto, "status": status, "button": button}

    def toggle_gg(self):
        st = self.gg_status()
        if st["running"] or st["autostart"]:
            gg.stop()
            if st["autostart"]:
                gg.set_autostart(False)
            QTimer.singleShot(1500, lambda: (self.io.submit(self.base.hardware_volume_mode), self.comp.reset()))
            msg = t("gg_stopped")
        else:
            gg.set_autostart(True)
            gg.start()
            msg = t("gg_started")
        return {**self.gg_status(), "message": msg}

    def quit(self):
        self.poll.stop()
        self.comp.stop()
        self.media.stop()
        self.io.submit(oled.steelseries_ui, self.base)
        self.io.shutdown(wait=True)
        self.watcher.stop()
        self.base.stop()
        self.tray.hide()
        self.qapp.quit()


def main():
    system.set_app_id("NovaPanel")
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("NovaPanel")
    qapp.setApplicationVersion(__version__)
    qapp.setWindowIcon(QIcon(str(ICON)))
    cfg = config.load()
    i18n.set_language(cfg["language"])
    if getattr(sys, "frozen", False) and not cfg["autostart_offered"]:
        system.set_autostart(True)
        cfg["autostart_offered"] = True
        config.save(cfg)

    # une seule instance : la deuxieme demande a la premiere d'ouvrir sa fenetre
    probe = QLocalSocket()
    probe.connectToServer("NovaPanel")
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.waitForBytesWritten(300)
        return
    QLocalServer.removeServer("NovaPanel")
    server = QLocalServer()
    server.listen("NovaPanel")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "NovaPanel", t("no_tray"))
        return
    panel = NovaPanel(qapp, show_window="--tray" not in sys.argv)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), panel.show_window()))
    sys.exit(qapp.exec())
