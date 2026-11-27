"""Glimra Remote – Verbindung zur GlimraApp (Handy) und Empfang beim Daten-Umzug.

HTTP-Server auf Port 8765 (Befehle) + UDP-Port 8766 (Suche im Heimnetz).
Ein Handy koppelt sich einmal mit einem 6-stelligen Code und bekommt einen Schlüssel.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import socket
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HTTP_PORT = 8765
UDP_PORT = 8766
MAX_UPLOAD = 4 * 1024 ** 3  # 4 GB


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def safe_relpath(raw: str) -> Path | None:
    """Macht aus einem fremden Pfad einen sicheren relativen Pfad (kein ../, kein /)."""
    parts = [p for p in raw.replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts or any(p == ".." or ":" in p or p.startswith("~") for p in parts):
        return None
    return Path(*parts)


class RemoteServer:
    def __init__(self, bridge, config_dir: Path, http_port: int = HTTP_PORT, udp_port: int = UDP_PORT):
        """bridge: Objekt mit Methoden status(), lock(), clipboard_get(), clipboard_set(t),
        notify(t), power(a), open_url(u), display_name()"""
        self.bridge = bridge
        self.http_port = http_port
        self.udp_port = udp_port
        self.devices_file = config_dir / "devices.json"
        self.pair_code = self._new_code()
        self.transfer_code = self._new_code()
        self.http: ThreadingHTTPServer | None = None
        self.udp_stop = threading.Event()
        self.on_change = lambda: None
        self.on_transfer = lambda path: None

    # ---------------------------------------------------------- Geräte
    @staticmethod
    def _new_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def new_pair_code(self) -> str:
        self.pair_code = self._new_code()
        self.on_change()
        return self.pair_code

    def new_transfer_code(self) -> str:
        self.transfer_code = self._new_code()
        self.on_change()
        return self.transfer_code

    def devices(self) -> list[dict]:
        try:
            return json.loads(self.devices_file.read_text())
        except (OSError, ValueError):
            return []

    def _save_devices(self, devs: list[dict]) -> None:
        self.devices_file.parent.mkdir(parents=True, exist_ok=True)
        self.devices_file.write_text(json.dumps(devs, indent=2, ensure_ascii=False))
        self.devices_file.chmod(0o600)
        self.on_change()

    def remove_device(self, name: str) -> None:
        self._save_devices([d for d in self.devices() if d.get("name") != name])

    def _device_for(self, token: str) -> dict | None:
        h = _hash(token)
        for d in self.devices():
            if secrets.compare_digest(d.get("token", ""), h):
                return d
        return None

    # ---------------------------------------------------------- Start/Stopp
    @property
    def running(self) -> bool:
        return self.http is not None

    def start(self) -> bool:
        if self.http:
            return True
        try:
            self.http = ThreadingHTTPServer(("0.0.0.0", self.http_port), self._handler())
        except OSError:
            self.http = None
            return False
        # selten aufwachen: spart CPU/Strom im Leerlauf
        threading.Thread(target=self.http.serve_forever, kwargs={"poll_interval": 5}, daemon=True).start()
        self.udp_stop.clear()
        self._udp_sock = None
        threading.Thread(target=self._udp_loop, daemon=True).start()
        return True

    def stop(self) -> None:
        if self.http:
            srv, self.http = self.http, None
            threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()), daemon=True).start()
        self.udp_stop.set()
        if getattr(self, "_udp_sock", None):
            try:
                self._udp_sock.close()   # weckt den blockierenden Empfang auf
            except OSError:
                pass

    def _udp_loop(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", self.udp_port))
        except OSError:
            return
        self._udp_sock = s
        while not self.udp_stop.is_set():
            try:
                data, addr = s.recvfrom(256)   # blockiert ohne Zeitlimit – 0 % CPU im Leerlauf
            except OSError:
                break
            if data.strip() == b"GLIMRA?":
                reply = {"glimra": 1, "type": "desktop", "name": socket.gethostname(),
                         "user": self.bridge.display_name(), "port": self.http_port}
                try:
                    s.sendto(json.dumps(reply).encode(), addr)
                except OSError:
                    pass
        try:
            s.close()
        except OSError:
            pass

    # ---------------------------------------------------------- HTTP
    def _handler(self):
        remote = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "GlimraRemote/1"

            def log_message(self, *args):
                pass

            def _send(self, code: int, data) -> None:
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Glimra-Code, X-Glimra-Path, X-Filename")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.end_headers()

            def _json(self) -> dict:
                n = min(int(self.headers.get("Content-Length", 0) or 0), 1_000_000)
                try:
                    return json.loads(self.rfile.read(n) or b"{}")
                except ValueError:
                    return {}

            def _device(self) -> dict | None:
                auth = self.headers.get("Authorization", "")
                if not auth.startswith("Bearer "):
                    return None
                return remote._device_for(auth[7:].strip())

            def _receive(self, target: Path) -> int:
                length = int(self.headers.get("Content-Length", 0) or 0)
                if length <= 0 or length > MAX_UPLOAD:
                    raise ValueError("Ungültige Dateigröße")
                target.parent.mkdir(parents=True, exist_ok=True)
                remaining = length
                with open(target, "wb") as f:
                    while remaining:
                        chunk = self.rfile.read(min(1 << 20, remaining))
                        if not chunk:
                            raise ValueError("Übertragung abgebrochen")
                        f.write(chunk)
                        remaining -= len(chunk)
                return length

            def do_GET(self):
                if self.path == "/hello":
                    return self._send(200, {"glimra": 1, "name": socket.gethostname()})
                if self.path == "/transfer-check":
                    if secrets.compare_digest(self.headers.get("X-Glimra-Code", ""), remote.transfer_code):
                        return self._send(200, {"ok": True, "name": socket.gethostname()})
                    time.sleep(1)
                    return self._send(403, {"error": "Falscher Umzugs-Code"})
                if not self._device():
                    return self._send(401, {"error": "Nicht gekoppelt"})
                if self.path == "/status":
                    return self._send(200, remote.bridge.status())
                if self.path == "/clipboard":
                    return self._send(200, {"text": remote.bridge.clipboard_get()})
                self._send(404, {"error": "Unbekannt"})

            def do_POST(self):
                # Umzug vom Windows-PC (Setup-Manager): eigener Code, keine Kopplung nötig
                if self.path == "/transfer":
                    if not secrets.compare_digest(self.headers.get("X-Glimra-Code", ""), remote.transfer_code):
                        time.sleep(1)
                        return self._send(403, {"error": "Falscher Umzugs-Code"})
                    rel = safe_relpath(urllib.parse.unquote(self.headers.get("X-Glimra-Path", "")))
                    if rel is None:
                        return self._send(400, {"error": "Ungültiger Pfad"})
                    target = Path.home() / "Umzug" / rel
                    try:
                        self._receive(target)
                    except (ValueError, OSError) as e:
                        return self._send(400, {"error": str(e)})
                    remote.on_transfer(str(target))
                    return self._send(200, {"ok": True})

                if self.path == "/pair":
                    data = self._json()
                    if not secrets.compare_digest(str(data.get("code", "")), remote.pair_code):
                        time.sleep(1.5)
                        return self._send(403, {"error": "Falscher Code"})
                    name = str(data.get("device", "Handy"))[:40] or "Handy"
                    token = secrets.token_urlsafe(32)
                    devs = [d for d in remote.devices() if d.get("name") != name]
                    devs.append({"name": name, "token": _hash(token), "since": time.strftime("%d.%m.%Y %H:%M")})
                    remote._save_devices(devs)
                    remote.new_pair_code()  # Code ist nur einmal gültig
                    return self._send(200, {"token": token, "name": socket.gethostname()})

                if not self._device():
                    return self._send(401, {"error": "Nicht gekoppelt"})

                if self.path == "/upload":
                    name = safe_relpath(urllib.parse.unquote_plus(self.headers.get("X-Filename", "datei")))
                    if name is None:
                        return self._send(400, {"error": "Ungültiger Dateiname"})
                    target = Path.home() / "Downloads" / name.name
                    try:
                        size = self._receive(target)
                    except (ValueError, OSError) as e:
                        return self._send(400, {"error": str(e)})
                    remote.bridge.notify(f"Datei vom Handy empfangen: {target.name}")
                    return self._send(200, {"ok": True, "size": size})

                data = self._json()
                b = remote.bridge
                if self.path == "/lock":
                    b.lock()
                elif self.path == "/clipboard":
                    b.clipboard_set(str(data.get("text", ""))[:100_000])
                elif self.path == "/notify":
                    b.notify("Vom Handy: " + str(data.get("text", ""))[:300])
                elif self.path == "/open":
                    url = str(data.get("url", ""))
                    if not url.startswith(("http://", "https://")):
                        return self._send(400, {"error": "Nur Web-Links"})
                    b.open_url(url)
                elif self.path == "/power":
                    if data.get("action") not in ("poweroff", "reboot", "suspend"):
                        return self._send(400, {"error": "Unbekannte Aktion"})
                    b.power(data["action"])
                elif self.path == "/volume":
                    if data.get("action") not in ("up", "down", "mute"):
                        return self._send(400, {"error": "Unbekannte Aktion"})
                    b.volume(data["action"])
                elif self.path == "/media":
                    if data.get("action") not in ("play-pause", "next", "previous"):
                        return self._send(400, {"error": "Unbekannte Aktion"})
                    b.media(data["action"])
                else:
                    return self._send(404, {"error": "Unbekannt"})
                self._send(200, {"ok": True})

        return Handler
