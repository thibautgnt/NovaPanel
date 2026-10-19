"""Ce qui depend du systeme d'exploitation, meme interface partout."""
import sys

if sys.platform == "win32":
    from . import windows as _os
elif sys.platform == "darwin":
    from . import macos as _os
else:
    from . import linux as _os

HOTKEYS = _os.HOTKEYS
SHELL_APPS = _os.SHELL_APPS
idle_seconds = _os.idle_seconds
foreground_app = _os.foreground_app
window_apps = _os.window_apps
style_window = _os.style_window
set_app_id = _os.set_app_id
autostart_enabled = _os.autostart_enabled
set_autostart = _os.set_autostart
SystemWatcher = _os.SystemWatcher
