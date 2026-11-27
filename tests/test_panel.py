import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
from glimra_panel import server as panel


@pytest.fixture
def srv(tmp_path, free_port, monkeypatch):
    monkeypatch.setattr(panel, "CONF_FILE", tmp_path / "panel.json")
    panel.set_password("geheim1234")
    port = free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), panel.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()


def call(base, path, data=None, cookie=None, headers=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    if cookie:
        h["Cookie"] = cookie
    r = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read()), resp.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), ""


def login(base):
    st, _, ck = call(base, "/api/login", {"password": "geheim1234"})
    assert st == 200
    return ck.split(";")[0]


def test_password_hashed(srv, tmp_path):
    assert "geheim1234" not in (tmp_path / "panel.json").read_text()


def test_needs_login(srv):
    assert call(srv, "/api/status")[0] == 401


def test_wrong_password(srv):
    assert call(srv, "/api/login", {"password": "falsch"})[0] == 403


def test_login_and_status(srv):
    ck = login(srv)
    st, data, _ = call(srv, "/api/status", cookie=ck)
    assert st == 200 and "hostname" in data


def test_cookie_flags(srv):
    _, _, ck = call(srv, "/api/login", {"password": "geheim1234"})
    assert "HttpOnly" in ck and "SameSite=Strict" in ck


def test_foreign_origin_blocked(srv):
    ck = login(srv)
    st, _, _ = call(srv, "/api/update", {}, cookie=ck, headers={"Origin": "http://evil.example"})
    assert st == 403


def test_service_whitelist(srv):
    ck = login(srv)
    assert call(srv, "/api/services", {"name": "evil", "action": "start"}, ck)[0] == 400
    assert call(srv, "/api/services", {"name": "sshd", "action": "mask"}, ck)[0] == 400
    assert call(srv, "/api/services", {"name": "NetworkManager", "action": "stop"}, ck)[0] == 400


def test_user_validation(srv):
    ck = login(srv)
    assert call(srv, "/api/users", {"name": "Bad Name", "password": "langesPasswort"}, ck)[0] == 400
    assert call(srv, "/api/users", {"name": "lisa", "password": "kurz"}, ck)[0] == 400


def test_icons_no_traversal(srv):
    with urllib.request.urlopen(srv + "/icons/power.svg") as r:
        assert r.headers["Content-Type"] == "image/svg+xml"
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(srv + "/icons/..%2Fserver.py")
