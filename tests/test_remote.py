import json
import socket
import urllib.error
import urllib.request

import pytest
from glimra_shell.remote import RemoteServer, safe_relpath


class FakeBridge:
    def __init__(self):
        self.events = []
        self.clip = "vom PC"

    def status(self):
        return {"hostname": "test", "user": "Leon"}

    def lock(self):
        self.events.append("lock")

    def clipboard_get(self):
        return self.clip

    def clipboard_set(self, t):
        self.clip = t

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

    def display_name(self):
        return "Leon"


@pytest.fixture
def server(tmp_path, free_port, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    bridge = FakeBridge()
    srv = RemoteServer(bridge, tmp_path / "cfg", http_port=free_port(), udp_port=free_port())
    assert srv.start()
    yield srv, bridge
    srv.stop()


def req(srv, path, data=None, token=None, headers=None, raw=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = "Bearer " + token
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    r = urllib.request.Request(f"http://127.0.0.1:{srv.http_port}{path}", data=body, headers=h,
                               method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def pair(srv):
    st, d = req(srv, "/pair", {"code": srv.pair_code, "device": "Pixel"})
    assert st == 200
    return d["token"]


def test_requires_pairing(server):
    srv, _ = server
    assert req(srv, "/status")[0] == 401
    assert req(srv, "/lock", {})[0] == 401


def test_wrong_code(server):
    srv, _ = server
    assert req(srv, "/pair", {"code": "000000" if srv.pair_code != "000000" else "111111"})[0] == 403


def test_code_only_once(server):
    srv, _ = server
    old = srv.pair_code
    pair(srv)
    assert srv.pair_code != old
    assert req(srv, "/pair", {"code": old, "device": "x"})[0] == 403


def test_commands(server):
    srv, bridge = server
    tok = pair(srv)
    assert req(srv, "/status", token=tok) == (200, {"hostname": "test", "user": "Leon"})
    assert req(srv, "/lock", {}, tok)[0] == 200
    assert req(srv, "/clipboard", {"text": "Hallo"}, tok)[0] == 200
    assert req(srv, "/clipboard", token=tok)[1]["text"] == "Hallo"
    assert req(srv, "/open", {"url": "file:///etc/passwd"}, tok)[0] == 400
    assert req(srv, "/power", {"action": "rm -rf"}, tok)[0] == 400
    assert "lock" in bridge.events


def test_token_stored_hashed(server):
    srv, _ = server
    tok = pair(srv)
    assert tok not in srv.devices_file.read_text()


def test_remove_device(server):
    srv, _ = server
    tok = pair(srv)
    srv.remove_device("Pixel")
    assert req(srv, "/status", token=tok)[0] == 401


def test_upload_and_transfer(server, tmp_path):
    srv, _ = server
    tok = pair(srv)
    st, _ = req(srv, "/upload", token=tok, headers={"X-Filename": "mein+foto.jpg"}, raw=b"abc")
    assert st == 200 and (tmp_path / "Downloads" / "mein foto.jpg").read_bytes() == b"abc"
    st, _ = req(srv, "/transfer", headers={"X-Glimra-Code": srv.transfer_code, "X-Glimra-Path": "Bilder/a.jpg"}, raw=b"x")
    assert st == 200 and (tmp_path / "Umzug" / "Bilder" / "a.jpg").exists()
    st, _ = req(srv, "/transfer", headers={"X-Glimra-Code": srv.transfer_code, "X-Glimra-Path": "../../evil"}, raw=b"x")
    assert st == 400


def test_discovery(server):
    srv, _ = server
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    s.sendto(b"GLIMRA?", ("127.0.0.1", srv.udp_port))
    data = json.loads(s.recv(500))
    assert data["type"] == "desktop" and data["port"] == srv.http_port


@pytest.mark.parametrize("raw,ok", [("Bilder/a.jpg", True), ("../x", False), ("/etc/passwd", True),
                                    ("a/../../b", False), ("C:/Windows", False), ("~/x", False), ("", False)])
def test_safe_relpath(raw, ok):
    r = safe_relpath(raw)
    assert (r is not None) == ok
    if r is not None:
        assert not r.is_absolute() and ".." not in r.parts
