"""Signale qu'une nouvelle version est publiee sur GitHub. Ne telecharge rien."""
import json
import threading
import urllib.request

from . import __version__

API = "https://api.github.com/repos/thibautgnt/NovaPanel/releases/latest"


def parse(version):
    return tuple(int(p) for p in version.lstrip("v").split(".")[:3] if p.isdigit())


def latest():
    """(version, url de la page de la version) ou None si rien de plus recent ou pas de reseau."""
    req = urllib.request.Request(API, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": f"NovaPanel/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
    except (OSError, ValueError):
        return None
    tag, url = data.get("tag_name", ""), data.get("html_url", "")
    if parse(tag) > parse(__version__) and url.startswith("https://github.com/thibautgnt/NovaPanel/"):
        return tag.lstrip("v"), url
    return None


def check_async(on_result):
    threading.Thread(target=lambda: on_result(latest()), daemon=True, name="updates").start()
