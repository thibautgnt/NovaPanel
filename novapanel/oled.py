"""Ecran OLED 128x64 de la base."""
from PIL import Image

W, H = 128, 64


def draw(base, img):
    """Affiche une image Pillow (convertie en noir et blanc 128x64)."""
    img = img.convert("1").resize((W, H)) if img.size != (W, H) else img.convert("1")
    px = img.load()
    # 2 blocs de 64x64 ; colonne par colonne, 8 lignes par octet (bit 0 = ligne du haut)
    for x0 in (0, 64):
        data = bytearray()
        for x in range(x0, x0 + 64):
            for yb in range(0, H, 8):
                byte = 0
                for bit in range(8):
                    if px[x, yb + bit]:
                        byte |= 1 << bit
                data.append(byte)
        report = bytes([0x06, 0x93, x0, 0, 64, 64]) + bytes(data)
        if not base.feature(report.ljust(1024, b"\0")):
            return False
    return True


def black(base):
    return draw(base, Image.new("1", (W, H), 0))


def steelseries_ui(base):
    """Rend l'ecran a l'affichage d'origine de la base."""
    return base.write(0x06, 0x95)
