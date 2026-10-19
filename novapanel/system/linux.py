"""Linux : demarrage avec la session. Le reste n'est pas encore pris en charge."""
import sys
from pathlib import Path

HOTKEYS = False
SHELL_APPS = set()

DESKTOP = Path.home() / ".config/autostart/novapanel.desktop"


# shortcut: pas d'inactivite, de verrouillage ni d'appli au premier plan sous Linux
# (X11 et Wayland different) ; a faire via logind / D-Bus si quelqu'un le demande
def idle_seconds():
    return 0


def foreground_app():
    return None


def window_apps():
    return []


def style_window(widget):
    pass


def set_app_id(name):
    pass


def autostart_enabled():
    return DESKTOP.exists()


def set_autostart(on):
    if not on:
        DESKTOP.unlink(missing_ok=True)
        return
    cmd = f'"{sys.executable}" --tray' if getattr(sys, "frozen", False) else f'"{sys.executable}" -m novapanel --tray'
    DESKTOP.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP.write_text(f"[Desktop Entry]\nType=Application\nName=NovaPanel\nExec={cmd}\n", encoding="utf-8")


class SystemWatcher:
    def __init__(self, on_event):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def set_hotkeys(self, hotkeys):
        pass
