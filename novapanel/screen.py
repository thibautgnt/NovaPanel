"""Ecran OLED 128x64 de la base.

Priorites, la premiere qui s'applique gagne :
  1. ecran noir (inactivite, verrouillage, force)
  2. annonces temporaires (reduction de bruit, volume, batterie faible)
  3. micro coupe
  4. page NovaPanel (horloge, musique, PC) en mode "custom"
  5. sinon, affichage d'origine de la base
"""
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil
from PIL import Image, ImageDraw, ImageFont

from . import i18n, oled
from .device import battery_percent
from .system import idle_seconds

W, H = 128, 64
FONTS = Path(__file__).resolve().parent / "fonts"


def _font(weight, size):
    return ImageFont.truetype(str(FONTS / f"BarlowSemiCondensed-{weight}.ttf"), size)


F_BIG = _font("SemiBold", 34)
F_MED = _font("SemiBold", 16)
F_SMALL = _font("SemiBold", 13)
F_TINY = _font("Medium", 12)


def _canvas():
    img = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"  # pas d'anticrenelage : pixels nets
    return img, d


def _center(d, y, text, font):
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, y), text, font=font, fill=1)


def icon_battery(d, x, y, level, w=22, h=10):
    d.rectangle((x, y, x + w - 3, y + h - 1), outline=1)
    d.rectangle((x + w - 2, y + 3, x + w - 1, y + h - 4), fill=1)
    fill = round((w - 7) * level / 8)
    if fill:
        d.rectangle((x + 2, y + 2, x + 1 + fill, y + h - 3), fill=1)


def icon_headset(d, x, y):
    d.arc((x, y, x + 12, y + 12), 180, 360, fill=1)
    d.rectangle((x, y + 6, x + 2, y + 11), fill=1)
    d.rectangle((x + 10, y + 6, x + 12, y + 11), fill=1)


def icon_mic(d, x, y, scale=1, crossed=False):
    s = scale
    d.rounded_rectangle((x + 4 * s, y, x + 10 * s, y + 11 * s), radius=3 * s, fill=1)
    d.arc((x + 1 * s, y + 4 * s, x + 13 * s, y + 15 * s), 0, 180, fill=1, width=s)
    d.line((x + 7 * s, y + 15 * s, x + 7 * s, y + 18 * s), fill=1, width=s)
    d.line((x + 3 * s, y + 18 * s, x + 11 * s, y + 18 * s), fill=1, width=s)
    if crossed:
        d.line((x - 1 * s, y + 19 * s, x + 15 * s, y - 1 * s), fill=0, width=3 * s)
        d.line((x - 1 * s, y + 19 * s, x + 15 * s, y - 1 * s), fill=1, width=s)


def icon_anc(d, x, y, mode):
    # 0 : cercle vide, 1 : ondes (transparence), 2 : cercle plein (ANC)
    if mode == 2:
        d.ellipse((x, y, x + 9, y + 9), fill=1)
    elif mode == 1:
        d.ellipse((x + 3, y + 3, x + 6, y + 6), fill=1)
        d.arc((x, y, x + 9, y + 9), 300, 60, fill=1)
        d.arc((x, y, x + 9, y + 9), 120, 240, fill=1)
    else:
        d.ellipse((x, y, x + 9, y + 9), outline=1)


def page_clock(state, shift=(0, 0)):
    img, d = _canvas()
    sx, sy = shift
    now = datetime.now()
    _center(d, -1 + sy, now.strftime("%H:%M"), F_BIG)
    days, months = i18n.t("oled_days"), i18n.t("oled_months")
    date = i18n.t("oled_date", day=days[now.weekday()], d=now.day, month=months[now.month - 1])
    _center(d, 34 + sy, date, F_TINY)
    _status_row(d, state, 51 + sy, sx)
    return img


def page_music(state, media, t, shift=(0, 0)):
    if not media or not media.get("title"):
        return page_clock(state, shift)
    img, d = _canvas()
    sx, sy = shift
    playing = media.get("playing")
    # icone lecture / pause
    if playing:
        d.polygon([(4 + sx, 3 + sy), (4 + sx, 11 + sy), (11 + sx, 7 + sy)], fill=1)
    else:
        d.rectangle((4 + sx, 3 + sy, 6 + sx, 11 + sy), fill=1)
        d.rectangle((9 + sx, 3 + sy, 11 + sx, 11 + sy), fill=1)
    d.text((16 + sx, 1 + sy), datetime.now().strftime("%H:%M"), font=F_SMALL, fill=1)
    _marquee(d, media["title"], F_MED, 17 + sy, t)
    _marquee(d, media.get("artist", ""), F_TINY, 35 + sy, t)
    _status_row(d, state, 51 + sy, sx)
    return img


def page_pc(state, stats, shift=(0, 0)):
    img, d = _canvas()
    sx, sy = shift
    rows = [("CPU", stats.get("cpu", 0)), ("RAM", stats.get("ram", 0))]
    for i, (label, val) in enumerate(rows):
        y = 3 + i * 17 + sy
        d.text((2 + sx, y - 2), label, font=F_SMALL, fill=1)
        d.rectangle((32 + sx, y + 1, 100 + sx, y + 9), outline=1)
        fill = round(66 * val / 100)
        if fill:
            d.rectangle((34 + sx, y + 3, 33 + sx + fill, y + 7), fill=1)
        d.text((104 + sx, y - 1), f"{val:.0f}", font=F_TINY, fill=1)
    _status_row(d, state, 51 + sy, sx)
    return img


def _status_row(d, state, y, sx=0):
    """Ligne du bas : casque, batterie de rechange, mode ANC."""
    hs = state.get("headset")
    icon_headset(d, 2 + sx, y)
    if hs in ("online", "charging"):
        icon_battery(d, 18 + sx, y + 2, state.get("battery", 0))
        d.text((42 + sx, y - 1), f"{battery_percent(state.get('battery', 0))}%", font=F_TINY, fill=1)
    else:
        d.text((18 + sx, y - 1), i18n.t("oled_off"), font=F_TINY, fill=1)
    icon_battery(d, 72 + sx, y + 2, state.get("spare_battery", 0), w=16)
    d.text((90 + sx, y - 1), i18n.t("oled_spare"), font=F_TINY, fill=1)
    icon_anc(d, 116 + sx, y + 1, state.get("anc", 0))


def _marquee(d, text, font, y, t):
    w = d.textlength(text, font=font)
    if w <= W - 4:
        d.text(((W - w) / 2, y), text, font=font, fill=1)
        return
    gap = 30
    off = int(t * 25) % int(w + gap)
    x = 2 - off
    d.text((x, y), text, font=font, fill=1)
    d.text((x + w + gap, y), text, font=font, fill=1)


def overlay_mic_muted(state, t):
    img, d = _canvas()
    icon_mic(d, 10, 4, scale=2, crossed=True)
    top, bottom = i18n.t("oled_mic")
    d.text((48, 6), top, font=F_MED, fill=1)
    d.text((48, 23), bottom, font=F_MED, fill=1)
    _status_row(d, state, 52)
    return img


def overlay_anc(mode):
    img, d = _canvas()
    d.ellipse((52, 4, 76, 28), outline=1, width=2)
    if mode == 2:
        d.ellipse((58, 10, 70, 22), fill=1)
    elif mode == 1:
        d.arc((44, -4, 84, 36), 300, 60, fill=1, width=2)
        d.arc((44, -4, 84, 36), 120, 240, fill=1, width=2)
        d.ellipse((61, 13, 67, 19), fill=1)
    _center(d, 36, i18n.t("oled_anc")[mode] if mode < 3 else "", F_SMALL)
    return img


def overlay_volume(vol):
    img, d = _canvas()
    _center(d, 2, "VOLUME", F_SMALL)
    d.rounded_rectangle((8, 24, 119, 38), radius=4, outline=1)
    fill = round(107 * vol / 100)
    if fill:
        d.rounded_rectangle((10, 26, 10 + fill, 36), radius=3, fill=1)
    _center(d, 42, f"{vol} %", F_MED)
    return img


def overlay_text(title, line=""):
    img, d = _canvas()
    _center(d, 10, title, F_MED)
    if line:
        _center(d, 34, line, F_TINY)
    return img


def simulated_origin(state):
    """Approximation de l'ecran d'origine, pour le miroir dans l'interface."""
    img, d = _canvas()
    vol = state.get("volume", 0)
    d.arc((30, 4, 98, 72), 180, 360, fill=1, width=3)
    ang = 180 + 180 * vol / 100
    d.arc((30, 4, 98, 72), 180, ang, fill=1, width=7)
    _center(d, 24, f"{vol}", F_MED)
    _status_row(d, state, 52)
    return img


class Compositor:
    FPS = 6
    FAST_FPS = 25

    def __init__(self, base, cfg, on_frame=None, media=None):
        self.base, self.cfg = base, cfg
        self.on_frame = on_frame or (lambda img, info: None)
        self.media = media  # objet avec .current -> dict ou None
        self.state = {}
        self.forced_black = False
        self.locked = False
        self.suspended = False
        self._toast = None  # (image_fn, fin)
        self._sent = None   # derniere image envoyee (bytes) ou "origin"
        self._sent_at = 0
        self._force_until = 0  # renvoie l'image a chaque pas jusqu'a cette date
        self._stats = {}
        self._stats_at = 0
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="oled")

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def update_state(self, s):
        old, self.state = self.state, s
        if not old:
            return
        if "anc" in old and s.get("anc") != old.get("anc") and self.cfg["oled_toast_anc"]:
            self.toast(lambda: overlay_anc(s.get("anc", 0)), 2.5)
        if "volume" in old and s.get("volume") != old.get("volume"):
            # la base dessine sa propre barre de volume par-dessus notre image a chaque cran
            # de molette : on redessine aussitot, puis a cadence rapide le temps qu'elle abandonne
            self._force_until = time.monotonic() + 2.5
            self._wake.set()
            if self.cfg["oled_toast_volume"] and self._owns_screen():
                self.toast(lambda: overlay_volume(self.state.get("volume", 0)), 1.5)
        if not s.get("connected"):
            self._sent = None

    def toast(self, fn, seconds):
        with self._lock:
            self._toast = (fn, time.monotonic() + seconds)

    def reset(self):
        """A appeler quand la base a pu perdre son affichage (reveil, rebranchement)."""
        self._sent = None

    def want_black(self):
        idle_min = self.cfg["idle_minutes"]
        return (self.forced_black or self.suspended
                or (self.locked and self.cfg["black_on_lock"])
                or (idle_min > 0 and idle_seconds() >= idle_min * 60))

    def _owns_screen(self):
        """Vrai si NovaPanel dessine (sinon c'est l'ecran d'origine qui s'affiche)."""
        return self.cfg["screen_mode"] == "custom" or (
            self.state.get("mic_muted") and self.cfg["oled_mic_muted"])

    def _pc_stats(self):
        now = time.monotonic()
        if now - self._stats_at > 2:
            self._stats = {"cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent}
            self._stats_at = now
        return self._stats

    def compose(self, t):
        """Retourne (image, info) ; image None = ecran d'origine."""
        s = self.state
        if self.want_black():
            return Image.new("1", (W, H), 0), "black"
        with self._lock:
            toast = self._toast
            if toast and time.monotonic() > toast[1]:
                self._toast = toast = None
        if toast:
            return toast[0](), "toast"
        if s.get("mic_muted") and self.cfg["oled_mic_muted"] and s.get("headset") == "online":
            return overlay_mic_muted(s, t), "mic"
        if self.cfg["screen_mode"] == "custom":
            # decale l'image d'un pixel chaque minute pour menager l'OLED
            m = int(t // 60) % 4
            shift = [(0, 0), (1, 0), (1, 1), (0, 1)][m]
            page = self.cfg["screen_page"]
            if page == "rotate":
                page = ["clock", "music", "pc"][int(t // 10) % 3]
                if page == "music" and not (self.media and self.media.current):
                    page = "clock"
            if page == "music":
                return page_music(s, self.media.current if self.media else None, t, shift), "custom"
            if page == "pc":
                return page_pc(s, self._pc_stats(), shift), "custom"
            return page_clock(s, shift), "custom"
        return None, "origin"

    def _run(self):
        t0 = time.monotonic()
        while not self._stop.is_set():
            fast = time.monotonic() < self._force_until
            self._wake.wait(1 / (self.FAST_FPS if fast else self.FPS))
            self._wake.clear()
            try:
                self.step(time.monotonic() - t0)
            except Exception:
                pass

    def step(self, t):
        img, info = self.compose(t)
        connected = self.state.get("connected")
        now = time.monotonic()
        if img is None:
            if connected and self._sent != "origin":
                if oled.steelseries_ui(self.base):
                    self._sent = "origin"
            self.on_frame(simulated_origin(self.state), "origin")
            return
        raw = img.tobytes()
        # renvoie regulierement meme sans changement, au cas ou la base reprendrait la main
        # (molette, bouton, menu de la base...)
        if connected and (raw != self._sent or now - self._sent_at > 3 or now < self._force_until):
            if oled.draw(self.base, img):
                self._sent, self._sent_at = raw, now
        self.on_frame(img, info)

    def black_now(self):
        """Ecran noir immediat (veille, extinction) depuis n'importe quel thread."""
        oled.black(self.base)
        self._sent = Image.new("1", (W, H), 0).tobytes()
