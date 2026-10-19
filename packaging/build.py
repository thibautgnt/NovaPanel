"""Construit NovaPanel.exe (Windows) ou NovaPanel.app (macOS) avec PyInstaller."""
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "novapanel"
icon = "icon.ico" if sys.platform == "win32" else "icon.icns"
args = [
    str(ROOT / "packaging" / "launcher.py"),
    "--paths", str(ROOT),
    "--name", "NovaPanel", "--windowed", "--noconfirm", "--clean",
    "--icon", str(ROOT / "packaging" / icon),
    "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
    "--osx-bundle-identifier", "io.github.thibautgnt.novapanel",
]
for d in ("ui", "fonts", "assets"):
    args += ["--add-data", f"{PKG / d}{':'}novapanel/{d}"]
if sys.platform == "win32":
    args += ["--collect-submodules", "winrt"]
PyInstaller.__main__.run(args)
