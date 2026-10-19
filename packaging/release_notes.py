"""Affiche la section du CHANGELOG d'une version : python packaging/release_notes.py v1.2.0"""
import re
import sys
from pathlib import Path

version = re.escape(sys.argv[1].lstrip("v"))
text = (Path(__file__).resolve().parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
section = re.search(rf"^## \[{version}\][^\n]*\n(.*?)(?=^## \[|^\[)", text, re.S | re.M)
print(section.group(1).strip() if section else "")
