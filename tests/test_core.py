import sys
import time

import pytest

from novapanel import config, screen
from novapanel.autoeq import AutoEq
from novapanel.device import Base, battery_percent


def report(*data):
    return bytes(data).ljust(64, b"\0")


def test_parse_status_report():
    b = Base()
    b._parse(report(0x06, 0xB0, 1, 2, 0, 1, 6, 8, 7, 1, 2, 5, 3, 1, 0, 0x08))
    s = b.state
    assert s["battery"] == 6 and s["spare_battery"] == 8
    assert s["mic_muted"] is True and s["anc"] == 2 and s["headset"] == "online"
    assert s["bt_connected"] is True and s["transparency"] == 7


def test_parse_volume_and_events():
    b = Base()
    b._parse(report(0x07, 0x25, 0x00))
    assert b.state["volume"] == 100
    b._parse(report(0x07, 0x25, 0x38))
    assert b.state["volume"] == 0
    b._parse(report(0x07, 0xBD, 1))
    assert b.state["anc"] == 1
    b._parse(report(0x07, 0xBB, 1))
    assert b.state["mic_muted"] is True


def test_on_change_only_when_value_changes():
    seen = []
    b = Base(on_change=seen.append)
    b._parse(report(0x07, 0xBD, 2))
    b._parse(report(0x07, 0xBD, 2))
    assert len(seen) == 1


def test_write_without_device_fails_cleanly():
    assert Base().set("anc", 2) is False


def test_battery_percent():
    assert [battery_percent(x) for x in (0, 4, 8)] == [0, 50, 100]


def test_autoeq_applies_and_restores():
    calls = []
    eq = AutoEq(lambda target, app: calls.append((target, app)), ignored={"explorer.exe"})
    rules = [{"exe": "game.exe", "eq": "base:2"}]
    eq.check(rules, "base:0", "game.exe")
    eq.check(rules, "base:2", "game.exe")
    eq.check(rules, "base:2", "explorer.exe")
    eq.check(rules, "base:2", "browser.exe")
    assert calls == [("base:2", "game.exe"), ("base:0", None)]


class FakeBase:
    def __init__(self):
        self.reports = 0

    def feature(self, data):
        self.reports += 1
        return True

    def write(self, *data):
        return True


@pytest.fixture
def comp(monkeypatch):
    monkeypatch.setattr(screen, "idle_seconds", lambda: 0)
    return screen.Compositor(FakeBase(), dict(config.DEFAULTS))


def test_pages_are_oled_sized():
    st = {"headset": "online", "battery": 5, "spare_battery": 8, "anc": 1}
    imgs = [screen.page_clock(st), screen.page_pc(st, {"cpu": 10, "ram": 20}),
            screen.page_music(st, {"title": "A very long title that has to scroll", "artist": "B", "playing": True}, 4),
            screen.overlay_mic_muted(st, 0), screen.overlay_anc(2), screen.overlay_volume(40)]
    assert all(i.size == (128, 64) and i.mode == "1" for i in imgs)


def test_compose_priorities(comp):
    comp.state = {"connected": True, "headset": "online", "mic_muted": True}
    assert comp.compose(0)[1] == "mic"
    comp.cfg["screen_mode"] = "custom"
    comp.state = {"connected": True, "headset": "online"}
    assert comp.compose(0)[1] == "custom"
    comp.toast(lambda: screen.overlay_text("X"), 5)
    assert comp.compose(0)[1] == "toast"
    comp.forced_black = True
    assert comp.compose(0)[1] == "black"


def test_volume_change_redraws_every_step(comp):
    comp.cfg["screen_mode"] = "custom"
    comp.update_state({"connected": True, "headset": "online", "volume": 50})
    comp.step(0)
    sent = comp.base.reports
    comp.step(0)
    assert comp.base.reports == sent  # meme image : rien a renvoyer
    comp.update_state({"connected": True, "headset": "online", "volume": 52})
    assert comp._wake.is_set() and comp._force_until > time.monotonic()
    comp.step(0)
    comp.step(0)
    assert comp.base.reports == sent + 4  # deux images de deux blocs chacune


@pytest.mark.skipif(sys.platform != "win32", reason="raccourcis globaux : Windows seulement")
def test_parse_hotkey():
    from novapanel.system.windows import MOD_ALT, MOD_CONTROL, MOD_NOREPEAT, parse_hotkey
    assert parse_hotkey("Ctrl+Alt+N") == (MOD_NOREPEAT | MOD_CONTROL | MOD_ALT, ord("N"))
    assert parse_hotkey("F5") == (MOD_NOREPEAT, 0x74)
    assert parse_hotkey("Ctrl+Alt") is None
