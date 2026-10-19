"""Demo du site : la vraie interface et le vrai rendu de l'ecran, avec une base simulee."""
import base64
import json
import random
import sys
import types

import js

sys.modules["hid"] = types.ModuleType("hid")
sys.modules["psutil"] = types.SimpleNamespace(
    cpu_percent=lambda: random.uniform(6, 24),
    virtual_memory=lambda: types.SimpleNamespace(percent=46.0))
sys.modules["novapanel.system"] = types.SimpleNamespace(idle_seconds=lambda: 0)

from novapanel import __version__, config, i18n, screen  # noqa: E402

STATE = {"connected": True, "firmware": "02.18.00", "volume": 62, "gain": 2, "eq_preset": 4,
         "eq": [3, 2.5, 1, 0, -1, -0.5, 1, 2.5, 3.5, 2], "mic_volume": 8, "sidetone": 1, "line_out": 1,
         "oled_dim_timer": 3, "oled_brightness": 8, "home_screen": 0, "bt_power": 1, "bt_call": 1,
         "bt_connected": True, "battery": 6, "spare_battery": 8, "transparency": 6, "mic_muted": False,
         "anc": 2, "mic_led": 5, "auto_off": 4, "wireless_mode": 0, "headset": "online"}
CFG = dict(config.DEFAULTS, screen_mode="custom", language=js.npLang,
           eq_presets={"Games": [4, 3, 1, 0, 0, 1, 2, 3, 2, 1], "Podcast": [-2, -1, 0, 2, 3, 3, 2, 0, -1, -2]},
           eq_rules=[{"exe": "valorant.exe", "eq": "user:Games"}])
APPS = ["chrome.exe", "discord.exe", "spotify.exe", "steam.exe", "valorant.exe"]
i18n.set_language(CFG["language"])


class Media:
    current = {"title": "Midnight City", "artist": "M83", "playing": True}
    available = True


comp = screen.Compositor(None, CFG, media=Media())
comp.update_state(dict(STATE))
gg_on = False


def push():
    comp.update_state(dict(STATE))
    js.npEmit("stateChanged", json.dumps(STATE))


def gg_status():
    return {"running": gg_on, "autostart": gg_on, "status": i18n.t("gg_running" if gg_on else "gg_off"),
            "button": i18n.t("gg_stop" if gg_on else "gg_enable")}


class Api:
    def getState(self):
        return json.dumps(STATE)

    def getConfig(self):
        return json.dumps(CFG)

    def getStrings(self):
        return json.dumps({"lang": i18n.lang, **i18n.STRINGS[i18n.lang]})

    def getMeta(self):
        return json.dumps({"version": __version__, "platform": "win32", "autostart": True, "hotkeys": True,
                           "media": True, "gg": gg_status(), "forced_black": comp.forced_black,
                           "update": None, "firmware": STATE["firmware"]})

    def set(self, name, value):
        STATE[name] = int(value)
        push()

    def setEq(self, gains_json):
        STATE.update(eq_preset=4, eq=[max(-10, min(10, round(g * 2) / 2)) for g in json.loads(gains_json)])
        push()

    def setCfg(self, key, value_json):
        CFG[key] = json.loads(value_json)
        if key == "language":
            i18n.set_language(CFG[key])
        js.npEmit("configChanged", json.dumps(CFG))

    def refresh(self):
        push()

    def toggleBlack(self):
        comp.forced_black = not comp.forced_black
        js.npEmit("forcedBlack", comp.forced_black)

    def setAutostart(self, on):
        pass

    def toggleGG(self):
        global gg_on
        gg_on = not gg_on
        return json.dumps({**gg_status(), "message": i18n.t("gg_started" if gg_on else "gg_stopped")})

    def runningApps(self):
        return json.dumps(APPS)

    def nudgeVolume(self, step):
        STATE["volume"] = max(0, min(100, STATE["volume"] + step))
        push()

    def toggleMute(self):
        STATE["mic_muted"] = not STATE["mic_muted"]
        push()

    def frame(self, t):
        img, info = comp.compose(t)
        if img is None:
            img = screen.simulated_origin(comp.state)
        return json.dumps([base64.b64encode(img.tobytes()).decode(), info])


api = Api()
