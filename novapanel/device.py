"""Communication USB/HID avec la base Arctis Nova Pro Wireless.

Protocole repris de :
- https://github.com/Donimax/ggoled (ecran)
- https://github.com/Sapd/HeadsetControl (egaliseur, sidetone, batterie)
- https://github.com/loteran/Arctis-Sound-Manager (le reste)

Interface HID 4 de la base, deux collections :
- page 0xFFC0 : on y ecrit les commandes, les reponses reviennent dessus (id 0x06)
- page 0xFF00 : evenements spontanes de la base (id 0x07)
"""
import threading
import time

import hid

VID = 0x1038
PIDS = (0x12E0, 0x12E5, 0x225D)

GAP_S = 0.05  # GG espace ses commandes de 50 ms

OPCODES = {
    "eq_preset": 0x2E,        # 0 Flat, 1 Bass Boost, 2 Focus, 3 Smiley, 4 Custom
    "gain": 0x27,             # 1 bas, 2 haut
    "mic_volume": 0x37,       # 1..10
    "sidetone": 0x39,         # 0..3
    "line_out": 0x43,         # 1 haut-parleur, 2 stream
    "oled_dim_timer": 0x83,   # 0..6 (jamais, 1, 5, 10, 15, 30, 60 min)
    "oled_brightness": 0x85,  # 1..10
    "home_screen": 0x89,      # 0 detaille, 1 simple
    "bt_power": 0xB2,         # 0/1 bluetooth au demarrage
    "bt_call": 0xB3,          # 0 rien, 1 -12 dB, 2 coupe le jeu
    "transparency": 0xB9,     # 1..10
    "anc": 0xBD,              # 0 off, 1 transparence, 2 reduction de bruit
    "mic_led": 0xBF,          # 1..10
    "auto_off": 0xC1,         # 0..6 (jamais, 1, 5, 10, 15, 30, 60 min)
    "wireless_mode": 0xC3,    # 0 vitesse, 1 portee
}
TIMER_MINUTES = [0, 1, 5, 10, 15, 30, 60]
EQ_PRESETS = ["Flat", "Bass Boost", "Focus", "Smiley", "Perso"]


def _hexs(b):
    return " ".join(f"{x:02x}" for x in b)


class Base:
    """Connexion a la base. Thread-safe, se reconnecte toute seule.

    `on_change(state)` est appele (depuis un thread de fond) a chaque mise a jour
    de `state`, un dict des valeurs connues.
    """

    def __init__(self, on_change=None, debug=False):
        self.on_change = on_change or (lambda s: None)
        self.debug = debug
        self.state = {"connected": False}
        self._lock = threading.RLock()
        self._cmd = None   # collection 0xFFC0
        self._evt = None   # collection 0xFF00
        self._last_write = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="base-hid")

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)
        self._close()

    def _open(self):
        cmd = evt = None
        for d in hid.enumerate(VID, 0):
            if d["product_id"] not in PIDS or d["interface_number"] != 4:
                continue
            h = hid.device()
            h.open_path(d["path"])
            h.set_nonblocking(True)
            if d["usage_page"] == 0xFFC0:
                cmd = h
            elif d["usage_page"] == 0xFF00:
                evt = h
            else:
                h.close()
        if not cmd:
            for h in (evt,):
                if h:
                    h.close()
            return False
        with self._lock:
            self._cmd, self._evt = cmd, evt
        return True

    def _close(self):
        with self._lock:
            for h in (self._cmd, self._evt):
                if h:
                    try:
                        h.close()
                    except Exception:
                        pass
            self._cmd = self._evt = None

    def _run(self):
        while not self._stop.is_set():
            if not self._cmd:
                try:
                    if self._open():
                        self._set(connected=True)
                        self.refresh()
                    else:
                        self._stop.wait(3)
                        continue
                except Exception:
                    self._close()
                    self._stop.wait(3)
                    continue
            try:
                got = False
                for h in (self._cmd, self._evt):
                    if not h:
                        continue
                    with self._lock:
                        r = h.read(128)
                    if r:
                        got = True
                        self._parse(bytes(r))
                if not got:
                    self._stop.wait(0.02)
            except Exception:
                self._close()
                self._set(connected=False)

    def write(self, *data):
        """Envoie une commande (report de sortie 64 octets). Retourne True si ok."""
        with self._lock:
            if not self._cmd:
                return False
            wait = self._last_write + GAP_S - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                if self.debug:
                    print(">>", _hexs(data))
                ok = self._cmd.write(bytes(data).ljust(64, b"\0")) > 0
            except Exception:
                ok = False
            self._last_write = time.monotonic()
            return ok

    def feature(self, data):
        """Envoie un feature report (utilise pour dessiner sur l'ecran)."""
        with self._lock:
            if not self._cmd:
                return False
            for i in range(5):
                try:
                    if self._cmd.send_feature_report(data) > 0:
                        return True
                except Exception:
                    pass
                time.sleep(0.005 * (i + 1))
            return False

    def refresh(self):
        """Redemande toutes les valeurs a la base (reponses lues par le thread)."""
        for op in (0x10, 0x20, 0x80, 0xB0):
            self.write(0x06, op)

    def set(self, name, value):
        ok = self.write(0x06, OPCODES[name], int(value))
        if ok:
            self.write(0x06, 0x09)  # enregistre dans la base
            self._set(**{name: int(value)})
        return ok

    def set_eq(self, gains):
        """gains : 10 valeurs en dB, -10..+10 par pas de 0.5. Passe en preset Perso."""
        raw = [max(0, min(40, round(20 + 2 * g))) for g in gains]
        self.write(0x06, 0x2E, 4)
        ok = self.write(0x06, 0x33, *raw)
        if ok:
            self.write(0x06, 0x09)
            self._set(eq_preset=4, eq=[(r - 20) / 2 for r in raw])
        return ok

    def hardware_volume_mode(self):
        """Rend la molette a la base (volume materiel) : ce que fait GG en quittant."""
        self.write(0x06, 0x49, 0x00)
        self.write(0x06, 0x8D, 0x00)

    def _set(self, **kw):
        changed = {k: v for k, v in kw.items() if self.state.get(k) != v}
        if changed:
            self.state.update(changed)
            try:
                self.on_change(dict(self.state))
            except Exception:
                pass

    def _parse(self, b):
        if self.debug:
            print("<<", _hexs(b[:32]))
        rid, op = b[0], b[1]
        if rid == 0x06 and op == 0x10:
            self._set(firmware=b[2:].split(bytes(1))[0].decode("ascii", "replace"))
        elif rid == 0x06 and op == 0x20:
            self._set(
                volume=_volume(b[3]),
                gain=b[4],
                eq_preset=b[6],
                eq=[(x - 20) / 2 for x in b[7:17]],
                mic_volume=b[17],
                sidetone=b[18],
                line_out=b[19],
            )
        elif rid == 0x06 and op == 0x80:
            self._set(oled_dim_timer=b[2], oled_brightness=b[3], home_screen=b[5])
        elif rid == 0x06 and op == 0xB0:
            self._set(
                bt_power=b[2],
                bt_call=b[3],
                bt_connected=b[5] == 1,
                battery=b[6],
                spare_battery=b[7],
                transparency=b[8],
                mic_muted=b[9] == 1,
                anc=b[10],
                mic_led=b[11],
                auto_off=b[12],
                wireless_mode=b[13],
                headset=_headset(b[15]),
            )
        elif op == 0xB7:
            self._set(battery=b[2], spare_battery=b[3])
        elif rid == 0x07 and op == 0x25:
            self._set(volume=_volume(b[2]))
        elif rid == 0x07 and op == 0xB5:
            self._set(headset="online" if b[4] == 8 else "offline")
            self.write(0x06, 0xB0)
        elif rid == 0x07 and op == 0xBD:
            self._set(anc=b[2])
        elif rid == 0x07 and op == 0xB9:
            self._set(transparency=b[2])
        elif rid == 0x07 and op == 0xBB:
            self._set(mic_muted=b[2] == 1)
        elif rid == 0x07:
            # evenement inconnu : on relit l'etat complet
            self.write(0x06, 0xB0)


def _volume(raw):
    # molette : 0 = max, 0x38 = min
    return round(100 * (0x38 - min(raw, 0x38)) / 0x38)


def _headset(raw):
    return {0x01: "offline", 0x02: "charging", 0x08: "online"}.get(raw, "offline")


def battery_percent(level):
    """La base donne 9 niveaux (0..8)."""
    return round(level * 100 / 8)
