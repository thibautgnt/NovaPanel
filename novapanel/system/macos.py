"""macOS : inactivite, verrouillage, veille, appli au premier plan, demarrage."""
import ctypes
import plistlib
import sys
from pathlib import Path

from AppKit import NSWorkspace, NSApplicationActivationPolicyRegular
from Foundation import NSDistributedNotificationCenter, NSObject

HOTKEYS = False
SHELL_APPS = {"finder", "loginwindow", "dock", "python", "python3", "novapanel"}

_cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
_cg.CGEventSourceSecondsSinceLastEventType.restype = ctypes.c_double
_cg.CGEventSourceSecondsSinceLastEventType.argtypes = [ctypes.c_int, ctypes.c_uint32]


def idle_seconds():
    # kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
    return _cg.CGEventSourceSecondsSinceLastEventType(1, 0xFFFFFFFF)


def _name(app):
    url = app.executableURL() if app else None
    return url.lastPathComponent().lower() if url else None


def foreground_app():
    return _name(NSWorkspace.sharedWorkspace().frontmostApplication())


def window_apps():
    apps = NSWorkspace.sharedWorkspace().runningApplications()
    names = {_name(a) for a in apps if a.activationPolicy() == NSApplicationActivationPolicyRegular}
    return sorted(n for n in names if n and n not in SHELL_APPS)


def style_window(widget):
    pass


def set_app_id(name):
    pass


AGENT = Path.home() / "Library/LaunchAgents/io.github.thibautgnt.novapanel.plist"


def autostart_enabled():
    return AGENT.exists()


def set_autostart(on):
    if not on:
        AGENT.unlink(missing_ok=True)
        return
    if getattr(sys, "frozen", False):
        args = [sys.executable, "--tray"]
    else:
        args = [sys.executable, "-m", "novapanel", "--tray"]
    AGENT.parent.mkdir(parents=True, exist_ok=True)
    AGENT.write_bytes(plistlib.dumps({"Label": AGENT.stem, "ProgramArguments": args, "RunAtLoad": True}))


class _Observer(NSObject):
    def initWithCallback_(self, cb):
        self = self.init()
        self.cb = cb
        return self

    def locked_(self, _n):
        self.cb("lock")

    def unlocked_(self, _n):
        self.cb("unlock")

    def sleep_(self, _n):
        self.cb("suspend")

    def wake_(self, _n):
        self.cb("resume")

    def poweroff_(self, _n):
        self.cb("shutdown")


class SystemWatcher:
    """Memes evenements que sous Windows, sans raccourcis globaux.

    Les notifications arrivent sur la boucle principale (celle de Qt).
    """

    def __init__(self, on_event):
        self._obs = _Observer.alloc().initWithCallback_(on_event)

    def start(self):
        dist = NSDistributedNotificationCenter.defaultCenter()
        dist.addObserver_selector_name_object_(self._obs, "locked:", "com.apple.screenIsLocked", None)
        dist.addObserver_selector_name_object_(self._obs, "unlocked:", "com.apple.screenIsUnlocked", None)
        ws = NSWorkspace.sharedWorkspace().notificationCenter()
        ws.addObserver_selector_name_object_(self._obs, "sleep:", "NSWorkspaceWillSleepNotification", None)
        ws.addObserver_selector_name_object_(self._obs, "wake:", "NSWorkspaceDidWakeNotification", None)
        ws.addObserver_selector_name_object_(self._obs, "poweroff:", "NSWorkspaceWillPowerOffNotification", None)

    def stop(self):
        NSDistributedNotificationCenter.defaultCenter().removeObserver_(self._obs)
        NSWorkspace.sharedWorkspace().notificationCenter().removeObserver_(self._obs)

    def set_hotkeys(self, hotkeys):
        pass
