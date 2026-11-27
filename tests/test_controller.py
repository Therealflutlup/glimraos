"""Tests für „PCs steuern“ im Windows-Setup-Manager (steuert z. B. den Glimra-OS-Laptop)."""

import pytest
from glimra_setup import controller
from glimra_shell.remote import RemoteServer


class LinuxLikeBridge:
    """Verhält sich wie Glimra OS auf dem Laptop."""
    platform = "glimra"

    def __init__(self):
        self.events = []

    def status(self):
        return {"hostname": "leon-laptop", "user": "leon", "os": "Glimra OS 1.2.0", "features": ["processes", "kill"]}

    def display_name(self):
        return "leon"

    def lock(self):
        self.events.append("lock")

    def clipboard_get(self):
        return "vom Laptop"

    def clipboard_set(self, t):
        self.events.append(("clip", t))

    def notify(self, t):
        self.events.append(("notify", t))

    def power(self, a):
        self.events.append(("power", a))

    def open_url(self, u):
        self.events.append(("open", u))

    def volume(self, a):
        self.events.append(("volume", a))

    def media(self, a):
        self.events.append(("media", a))

    def handle_extra(self, method, path, data):
        if method == "GET" and path == "/processes":
            return 200, {"processes": [{"name": "firefox", "pid": 4242, "memText": "300 MB", "protected": False}]}
        if path == "/kill":
            self.events.append(("kill", data["pid"]))
            return 200, {"ok": True}
        return None


@pytest.fixture
def laptop(tmp_path, free_port, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    bridge = LinuxLikeBridge()
    srv = RemoteServer(bridge, tmp_path / "cfg", http_port=free_port(), udp_port=free_port())
    assert srv.start()
    yield srv, bridge
    srv.stop()


def test_discover_finds_laptop(laptop):
    srv, _ = laptop
    found = controller.discover(timeout=1.2, port=srv.udp_port, include_self=True)
    hit = [d for d in found if d["host"].endswith(f":{srv.http_port}")]
    assert hit and hit[0]["user"] == "leon" and hit[0]["platform"] == "glimra"


def test_pair_control_and_upload(laptop, tmp_path):
    srv, bridge = laptop
    host = f"127.0.0.1:{srv.http_port}"
    assert controller.pair(host, "12345")[0] is False                       # zu kurz
    ok, msg, _ = controller.pair(host, "000000" if srv.pair_code != "000000" else "111111")
    assert not ok and "Falsch" in msg
    ok, msg, dev = controller.pair(host, srv.pair_code, "PC Test")
    assert ok and dev["token"] and dev["name"]
    code, st = controller.request("GET", host, "/status", dev["token"])
    assert code == 200 and st["hostname"] == "leon-laptop"
    assert controller.request("POST", host, "/lock", dev["token"])[0] == 200
    assert controller.request("POST", host, "/volume", dev["token"], {"action": "up"})[0] == 200
    assert controller.request("GET", host, "/processes", dev["token"])[1]["processes"][0]["pid"] == 4242
    assert controller.request("POST", host, "/kill", dev["token"], {"pid": 4242})[0] == 200
    assert controller.request("GET", host, "/screen", dev["token"])[0] == 404     # Funktion fehlt → sauber 404
    f = tmp_path / "foto 1.jpg"
    f.write_bytes(b"x" * 5000)
    assert controller.upload(host, dev["token"], f)[0] == 200
    assert (tmp_path / "Downloads" / "foto 1.jpg").stat().st_size == 5000
    assert "lock" in bridge.events and ("volume", "up") in bridge.events and ("kill", 4242) in bridge.events


def test_unreachable_has_helpful_message(free_port):
    code, data = controller.request("GET", f"127.0.0.1:{free_port()}", "/status", timeout=2)
    assert code == 0 and "abgelehnt" in data["error"]


def test_store_roundtrip(tmp_path):
    store = tmp_path / "pcs.json"
    controller.remember({"host": "1.2.3.4:8765", "name": "Laptop", "token": "t"}, store)
    controller.remember({"host": "1.2.3.4:8765", "name": "Laptop neu", "token": "u"}, store)
    assert [d["name"] for d in controller.load(store)] == ["Laptop neu"]
    controller.forget("1.2.3.4:8765", store)
    assert controller.load(store) == []
    assert controller.normalize_host(" 192.168.178.40 ") == "192.168.178.40:8765"
