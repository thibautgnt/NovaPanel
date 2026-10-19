"""Reglages de NovaPanel, dans le dossier de configuration de l'utilisateur."""
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    DIR = Path(os.environ["APPDATA"]) / "NovaPanel"
elif sys.platform == "darwin":
    DIR = Path.home() / "Library/Application Support/NovaPanel"
else:
    DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "NovaPanel"
FILE = DIR / "config.json"

DEFAULTS = {
    "idle_minutes": 5,          # 0 = jamais
    "black_on_lock": True,
    "black_on_sleep": True,
    "black_on_shutdown": True,
    "low_battery_level": 2,     # sur 8 (2/8 = 25 %)
    "notify_spare_full": True,
    "eq_presets": {},           # nom -> 10 gains en dB
    # ecran de la base
    "screen_mode": "origin",    # "origin" (affichage SteelSeries) ou "custom"
    "screen_page": "clock",     # clock | music | pc | rotate
    "oled_mic_muted": True,     # "micro coupe" sur l'ecran tant qu'il est coupe
    "oled_toast_anc": True,     # annonce le mode de reduction de bruit
    "oled_toast_volume": True,  # barre de volume (quand NovaPanel dessine)
    # bulle a l'ecran du PC
    "osd": True,                # reduction de bruit, egaliseur auto, raccourcis...
    "osd_mic": False,           # micro coupe / active
    # raccourcis globaux : action -> touches
    "hotkeys": {"anc_cycle": "Ctrl+Alt+N", "screen_black": "Ctrl+Alt+B",
                "screen_page": "Ctrl+Alt+P"},
    # egaliseur automatique : [{"exe": "valorant.exe", "eq": "base:2" | "user:<nom>"}]
    "eq_rules": [],
}


def load():
    cfg = dict(DEFAULTS)
    try:
        cfg.update(json.loads(FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg):
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FILE)
