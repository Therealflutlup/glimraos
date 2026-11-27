"""„PCs steuern“: Vom Windows-PC aus andere Glimra-Geräte steuern (z. B. den Glimra-OS-Laptop).

Gleiches Protokoll wie die GlimraApp auf dem Handy: Suche per UDP 8766, Kopplung mit dem
6-stelligen Code, danach Befehle per HTTP 8765 mit dem Schlüssel des Geräts.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from glimra_shell.remote import HTTP_PORT, UDP_PORT

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Glimra"
STORE = CONFIG_DIR / "pcs.json"


# ------------------------------------------------------------------ gespeicherte Geräte
def load(store: Path = STORE) -> list[dict]:
    try:
        return json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def save(devices: list[dict], store: Path = STORE) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(devices, indent=2, ensure_ascii=False), encoding="utf-8")


def remember(device: dict, store: Path = STORE) -> None:
    devs = [d for d in load(store) if d["host"] != device["host"]]
    devs.append(device)
    save(devs, store)


def forget(host: str, store: Path = STORE) -> None:
    save([d for d in load(store) if d["host"] != host], store)


def normalize_host(text: str) -> str:
    text = text.strip().replace("http://", "").rstrip("/")
    return text if ":" in text else f"{text}:{HTTP_PORT}"


# ------------------------------------------------------------------ Netzwerk
def own_ips() -> set[str]:
    ips = {"127.0.0.1"}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return ips


def discover(timeout: float = 2.0, port: int = UDP_PORT, include_self: bool = False) -> list[dict]:
    """Sucht Glimra-Geräte im Heimnetz (Glimra OS, Glimra Server, Windows mit Agent)."""
    found: dict[str, dict] = {}
    mine = own_ips()
    targets = ["255.255.255.255"] + [ip.rsplit(".", 1)[0] + ".255" for ip in mine if ip != "127.0.0.1"]
    if include_self:
        targets.append("127.0.0.1")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.3)
    try:
        for _ in range(2):
            for t in targets:
                try:
                    s.sendto(b"GLIMRA?", (t, port))
                except OSError:
                    pass
        end = time.time() + timeout
        while time.time() < end:
            try:
                data, addr = s.recvfrom(1024)
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                break
            if addr[0] in mine and not include_self:
                continue
            try:
                info = json.loads(data)
            except ValueError:
                continue
            host = f"{addr[0]}:{info.get('port', HTTP_PORT)}"
            found[host] = {"host": host, "name": info.get("name", addr[0]), "user": info.get("user", ""),
                           "type": info.get("type", "desktop"), "platform": info.get("platform", "glimra")}
    finally:
        s.close()
    return sorted(found.values(), key=lambda d: d["name"].lower())


def request(method: str, host: str, path: str, token: str = "", body: dict | None = None,
            timeout: float = 8) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body or {}).encode() if method == "POST" else None
    req = urllib.request.Request(f"http://{host}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {"error": f"Fehler {e.code}"}
    except (urllib.error.URLError, OSError) as e:
        reason = getattr(e, "reason", e)
        if isinstance(reason, ConnectionRefusedError):
            return 0, {"error": "Verbindung abgelehnt – ist die Fernsteuerung am Gerät an?"}
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return 0, {"error": "Keine Antwort – gleiches Netzwerk? IP richtig? Firewall?"}
        return 0, {"error": f"Nicht erreichbar ({reason})"}


def pair(host: str, code: str, device_name: str | None = None) -> tuple[bool, str, dict]:
    """Koppelt diesen Windows-PC mit einem Gerät. Gibt (ok, Meldung, Gerät) zurück."""
    code = "".join(ch for ch in code if ch.isdigit())
    if len(code) != 6:
        return False, "Der Code hat 6 Ziffern.", {}
    status, data = request("POST", host, "/pair", body={"code": code, "device": device_name or f"PC {socket.gethostname()}"})
    if status == 200 and data.get("token"):
        dev = {"host": host, "name": data.get("name", host), "token": data["token"]}
        return True, f"Verbunden mit {dev['name']}.", dev
    return False, data.get("error", "Kopplung fehlgeschlagen"), {}


def upload(host: str, token: str, file: Path, timeout: float = 600) -> tuple[int, dict]:
    size = file.stat().st_size
    with open(file, "rb") as f:
        req = urllib.request.Request(f"http://{host}/upload", data=f, method="POST", headers={
            "Authorization": "Bearer " + token, "Content-Length": str(size),
            "Content-Type": "application/octet-stream", "X-Filename": urllib.parse.quote_plus(file.name)})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
        except (urllib.error.URLError, OSError) as e:
            return 0, {"error": f"Senden fehlgeschlagen ({getattr(e, 'reason', e)})"}
