"""Tests für den Glimra Agent unter Windows (GlimraApp steuert den Windows-PC)."""

import json
import struct
import urllib.error
import urllib.request
import zlib

import pytest
from glimra_setup import agent
from glimra_shell.remote import RemoteServer

TASKLIST = '''"System Idle Process","0","Services","0","8 K"
"svchost.exe","1234","Services","0","25.120 K"
"chrome.exe","8812","Console","1","412.304 K"
"Discord.exe","9100","Console","1","198.004 K"
'''

QUSER_EN = """ USERNAME              SESSIONNAME        ID  STATE   IDLE TIME  LOGON TIME
>leon                  console             1  Active      none   27.11.2026 18:02
 admin                                     2  Disc           3   27.11.2026 09:15
"""
QUSER_DE = """ BENUTZERNAME          SITZUNGSNAME       ID  STATUS  LEERLAUF   ANMELDEZEIT
>leon                  console             1  Aktiv       .      27.11.2026 18:02
"""


def test_parse_tasklist_sorts_and_protects():
    procs = agent.parse_tasklist(TASKLIST)
    assert [p["name"] for p in procs[:3]] == ["chrome.exe", "Discord.exe", "svchost.exe"]
    by = {p["name"]: p for p in procs}
    assert by["chrome.exe"]["pid"] == 8812 and by["chrome.exe"]["mem"] == 412304 * 1024
    assert by["svchost.exe"]["protected"] and not by["Discord.exe"]["protected"]


def test_parse_quser_english_and_german():
    us = agent.parse_quser(QUSER_EN)
    assert [(u["user"], u["state"], u["current"]) for u in us] == [("leon", "aktiv", True), ("admin", "getrennt", False)]
    assert us[0]["since"] == "27.11.2026 18:02"
    assert agent.parse_quser(QUSER_DE)[0]["state"] == "aktiv"


def test_png_encoder_produces_valid_png():
    w, h = 3, 2
    bgra = bytes([0, 0, 255, 255] * w * h)          # rot in BGRA
    rows = agent.bgra_to_rows(bgra, w, h)
    assert rows[0] == bytes([255, 0, 0] * w)
    png = agent.png_encode(w, h, rows)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    ihdr = png[16:29]
    assert struct.unpack(">II", ihdr[:8]) == (w, h)
    idat_len = struct.unpack(">I", png[33:37])[0]
    raw = zlib.decompress(png[41:41 + idat_len])
    assert raw == (b"\x00" + bytes([255, 0, 0] * w)) * h


def test_extra_commands_validate_input():
    b = agent.WindowsBridge()
    assert b.handle_extra("POST", "/kill", {"pid": "abc"})[0] == 400
    assert b.handle_extra("POST", "/kill", {"pid": 4})[0] == 404
    assert b.handle_extra("POST", "/launch", {"app": "cmd /c format c:"})[0] == 400
    assert b.handle_extra("POST", "/launch", {"app": "notepad"})[0] == 200
    assert b.handle_extra("POST", "/message", {"text": ""})[0] == 400
    assert b.handle_extra("POST", "/unbekannt", {}) is None
    code, data = b.handle_extra("GET", "/users", {})
    assert code == 200 and data["users"]


def test_status_reports_features_and_domain(monkeypatch):
    monkeypatch.setenv("USERDNSDOMAIN", "HEIM.LAN")
    st = agent.WindowsBridge().status()
    assert st["platform"] == "windows" and st["domain"] == "heim.lan"
    assert {"screen", "processes", "kill", "logoff", "users"} <= set(st["features"])
    assert {a["id"] for a in st["launch"]} >= {"explorer", "taskmgr"}


def _req(port, path, data=None, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=None if data is None else json.dumps(data).encode(),
                               headers=h, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


@pytest.fixture
def win_server(tmp_path, free_port):
    srv = RemoteServer(agent.WindowsBridge(), tmp_path, http_port=free_port(), udp_port=free_port())
    assert srv.start()
    yield srv
    srv.stop()


def test_agent_end_to_end(win_server):
    port = win_server.http_port
    # Setup-Manager liest Code und Geräte nur lokal
    code, info = _req(port, "/local/info")
    assert code == 200 and len(info["code"]) == 6 and info["devices"] == []
    # koppeln wie die Android-App
    code, data = _req(port, "/pair", {"code": info["code"], "device": "Pixel 8a"})
    assert code == 200
    token = data["token"]
    code, st = _req(port, "/status", token=token)
    assert code == 200 and st["platform"] == "windows" and "processes" in st["features"]
    assert _req(port, "/users", token=token)[0] == 200
    assert _req(port, "/launch", {"app": "evil"}, token=token)[0] == 400
    assert _req(port, "/gibtsnicht", {}, token=token)[0] == 404
    assert _req(port, "/processes")[0] == 401                      # ohne Kopplung nichts
    # Gerät im Setup-Manager entfernen
    code, info = _req(port, "/local/remove", {"name": "Pixel 8a"})
    assert code == 200 and info["devices"] == []
    assert _req(port, "/status", token=token)[0] == 401
    old = info["code"]
    assert _req(port, "/local/newcode", {})[0] == 200 and old


def test_agent_running_detection(win_server):
    assert agent.agent_running(win_server.http_port)
    assert not agent.agent_running(1)
