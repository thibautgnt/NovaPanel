import io
import json

from novapanel import updates


def fake_urlopen(payload):
    return lambda req, timeout: io.BytesIO(json.dumps(payload).encode())


def test_parse():
    assert updates.parse("v1.10.0") > updates.parse("1.9.3")
    assert updates.parse("1.1.0") == (1, 1, 0)


def test_newer_release_is_reported(monkeypatch):
    url = "https://github.com/thibautgnt/NovaPanel/releases/tag/v99.0.0"
    monkeypatch.setattr(updates.urllib.request, "urlopen", fake_urlopen({"tag_name": "v99.0.0", "html_url": url}))
    assert updates.latest() == ("99.0.0", url)


def test_same_or_foreign_release_is_ignored(monkeypatch):
    monkeypatch.setattr(updates.urllib.request, "urlopen",
                        fake_urlopen({"tag_name": "v" + updates.__version__, "html_url": "https://github.com/thibautgnt/NovaPanel/"}))
    assert updates.latest() is None
    monkeypatch.setattr(updates.urllib.request, "urlopen",
                        fake_urlopen({"tag_name": "v99.0.0", "html_url": "https://evil.example/"}))
    assert updates.latest() is None


def test_network_error_is_silent(monkeypatch):
    def boom(req, timeout):
        raise OSError("offline")
    monkeypatch.setattr(updates.urllib.request, "urlopen", boom)
    assert updates.latest() is None
