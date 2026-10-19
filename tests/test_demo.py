import base64
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import novapanel


def test_web_demo(monkeypatch):
    events = []
    monkeypatch.setitem(sys.modules, "js", SimpleNamespace(npLang="fr", npEmit=lambda *a: events.append(a)))
    # demo.py remplace ces modules par des bouchons : on les remet en place apres le test
    for name in ("hid", "psutil", "novapanel.system", "novapanel.screen"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.delattr(novapanel, "screen", raising=False)
    api = runpy.run_path(str(Path(__file__).parents[1] / "docs/demo/demo.py"))["api"]

    assert json.loads(api.getStrings())["lang"] == "fr"
    api.nudgeVolume(4)
    assert json.loads(events[-1][1])["volume"] == 66
    img, info = json.loads(api.frame(0.0))
    assert len(base64.b64decode(img)) == 128 * 64 // 8 and info == "toast"
    api.toggleBlack()
    assert events[-1] == ("forcedBlack", True)
    assert json.loads(api.frame(0.0))[1] == "black"
