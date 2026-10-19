"""Windows : inactivite, verrouillage, veille, extinction, raccourcis globaux, demarrage."""
import ctypes
import ctypes.wintypes as wt
import sys
import threading
import winreg
from pathlib import Path

import psutil

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)

HOTKEYS = True
SHELL_APPS = {"explorer.exe", "shellexperiencehost.exe", "searchhost.exe", "startmenuexperiencehost.exe",
              "textinputhost.exe", "applicationframehost.exe", "systemsettings.exe",
              "python.exe", "pythonw.exe", "novapanel.exe"}

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_POWERBROADCAST = 0x0218
WM_WTSSESSION_CHANGE = 0x02B1
WM_HOTKEY = 0x0312
WM_APP_HOTKEYS = 0x8001
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMEAUTOMATIC = 0x0012
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.restype = wt.HWND
user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND,
                                   wt.HMENU, wt.HINSTANCE, wt.LPVOID]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wt.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HBRUSH),
                ("lpszMenuName", wt.LPCWSTR), ("lpszClassName", wt.LPCWSTR)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("dwTime", wt.DWORD)]


class MARGINS(ctypes.Structure):
    _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]


def idle_seconds():
    lii = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    user32.GetLastInputInfo(ctypes.byref(lii))
    return ((kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF) / 1000


def _pid_name(pid):
    try:
        return psutil.Process(pid).name().lower()
    except (psutil.Error, ValueError):
        return None


def foreground_app():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return _pid_name(pid.value)


def window_apps():
    pids = set()
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pids.add(pid.value)
        return True

    user32.EnumWindows(EnumProc(cb), 0)
    return sorted({n for n in map(_pid_name, pids) if n and n not in SHELL_APPS})


def style_window(widget):
    hwnd = int(widget.winId())
    dwm = ctypes.windll.dwmapi
    # coins arrondis et barre de titre sombre (Windows 11), ombre malgre l'absence de bordure
    dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(2)), 4)
    dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
    dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(MARGINS(1, 1, 1, 1)))


def set_app_id(name):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(name)


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    pyw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pyw}" -m novapanel --tray'


def autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, "NovaPanel")
        return True
    except OSError:
        return False


def set_autostart(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, "NovaPanel", 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(k, "NovaPanel")
            except OSError:
                pass


def parse_hotkey(text):
    """'Ctrl+Alt+N' -> (modificateurs, code de touche) ou None."""
    mods, vk = MOD_NOREPEAT, None
    for part in text.replace(" ", "").split("+"):
        p = part.lower()
        if p in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif p == "alt":
            mods |= MOD_ALT
        elif p == "shift":
            mods |= MOD_SHIFT
        elif p == "win":
            mods |= MOD_WIN
        elif len(p) == 1 and p.isalnum():
            vk = ord(p.upper())
        elif p.startswith("f") and p[1:].isdigit() and 1 <= int(p[1:]) <= 24:
            vk = 0x70 + int(p[1:]) - 1
    return (mods, vk) if vk else None


class SystemWatcher:
    """Appelle `on_event(nom)` : lock, unlock, suspend, resume, shutdown, hotkey:<action>.

    Les rappels viennent d'un thread a part et doivent etre rapides
    (a la veille ou a l'extinction, Windows n'attend pas longtemps).
    """

    def __init__(self, on_event):
        self.on_event = on_event
        self.hwnd = None
        self._hotkeys = {}
        self._registered = {}
        self._proc = WNDPROC(self._wndproc)  # garder une reference, sinon ctypes la libere
        self._thread = threading.Thread(target=self._run, daemon=True, name="sys-watcher")

    def start(self):
        self._thread.start()

    def stop(self):
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def set_hotkeys(self, hotkeys):
        self._hotkeys = dict(hotkeys)
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_APP_HOTKEYS, 0, 0)

    def _apply_hotkeys(self, hwnd):
        for hid in list(self._registered):
            user32.UnregisterHotKey(hwnd, hid)
        self._registered.clear()
        failed = []
        for i, (action, text) in enumerate(self._hotkeys.items(), start=1):
            parsed = parse_hotkey(text or "")
            if not parsed:
                continue
            if user32.RegisterHotKey(hwnd, i, *parsed):
                self._registered[i] = action
            else:
                failed.append(text)
        if failed:
            self._emit("hotkey_failed:" + ", ".join(failed))

    def _emit(self, name):
        try:
            self.on_event(name)
        except Exception:
            pass

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == WM_WTSSESSION_CHANGE:
            if wparam == WTS_SESSION_LOCK:
                self._emit("lock")
            elif wparam == WTS_SESSION_UNLOCK:
                self._emit("unlock")
        elif msg == WM_POWERBROADCAST:
            if wparam == PBT_APMSUSPEND:
                self._emit("suspend")
            elif wparam == PBT_APMRESUMEAUTOMATIC:
                self._emit("resume")
            return 1
        elif msg == WM_HOTKEY:
            action = self._registered.get(wparam)
            if action:
                self._emit("hotkey:" + action)
            return 0
        elif msg == WM_APP_HOTKEYS:
            self._apply_hotkeys(hwnd)
            return 0
        elif msg == WM_QUERYENDSESSION:
            return 1
        elif msg == WM_ENDSESSION and wparam:
            self._emit("shutdown")
            return 0
        elif msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0
        elif msg == WM_DESTROY:
            wtsapi32.WTSUnRegisterSessionNotification(hwnd)
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _run(self):
        hinst = kernel32.GetModuleHandleW(None)
        cls = "NovaPanelWatcher"
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=hinst, lpszClassName=cls)
        user32.RegisterClassW(ctypes.byref(wc))
        # fenetre de haut niveau invisible : une fenetre "message-only" ne recoit
        # pas WM_POWERBROADCAST ni WM_ENDSESSION
        self.hwnd = user32.CreateWindowExW(0, cls, "NovaPanelWatcher", 0, 0, 0, 0, 0,
                                           None, None, hinst, None)
        wtsapi32.WTSRegisterSessionNotification(self.hwnd, 0)
        self._apply_hotkeys(self.hwnd)
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
