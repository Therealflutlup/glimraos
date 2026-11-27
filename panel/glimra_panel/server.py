"""Glimra Panel – Weboberfläche für Glimra OS Server.

Nur Python-Standardbibliothek, keine Zusatzpakete nötig.

  python3 -m glimra_panel                 Panel starten (Port 8080)
  python3 -m glimra_panel --set-password  Panel-Passwort setzen
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__

HERE = Path(__file__).resolve().parent
CONF_FILE = Path(os.environ.get("GLIMRA_PANEL_CONF", "/etc/glimra/panel.json"))
UPDATE_LOG = Path(os.environ.get("GLIMRA_UPDATE_LOG", "/var/log/glimra-update.log"))
CERT_FILE = Path(os.environ.get("GLIMRA_PANEL_CERT", "/etc/glimra/panel.crt"))
KEY_FILE = Path(os.environ.get("GLIMRA_PANEL_KEY", "/etc/glimra/panel.key"))
TLS = {"on": False}

# Dienste, die im Panel gesteuert werden dürfen
SERVICES = {
    "sshd": "SSH-Fernzugriff",
    "smb": "Dateifreigabe (Samba)",
    "docker": "Container (Docker)",
    "libvirtd": "Virtuelle Maschinen",
    "nginx": "Webserver",
    "NetworkManager": "Netzwerk",
    "grub-btrfsd": "Snapshot-Bootmenü",
}
SERVICE_ACTIONS = {"start", "stop", "restart", "enable", "disable"}
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")

SESSIONS: dict[str, float] = {}
SESSION_TTL = 8 * 3600
UPDATE_STATE = {"running": False, "exit": None}


# --------------------------------------------------------------- Passwort
def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def set_password(password: str) -> None:
    salt = secrets.token_bytes(16)
    CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONF_FILE.write_text(json.dumps({"salt": salt.hex(), "hash": _hash(password, salt)}))
    os.chmod(CONF_FILE, 0o600)


def check_password(password: str) -> bool:
    try:
        conf = json.loads(CONF_FILE.read_text())
    except (OSError, ValueError):
        return False
    return hmac.compare_digest(_hash(password, bytes.fromhex(conf["salt"])), conf["hash"])


# --------------------------------------------------------------- Systemdaten
def run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def status() -> dict:
    data = {
        "hostname": socket.gethostname(),
        "os": "Glimra OS Server",
        "kernel": platform.release(),
        "cpus": os.cpu_count(),
        "load": [round(x, 2) for x in os.getloadavg()],
    }
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                data["os"] = line.split("=", 1)[1].strip('"')
    except OSError:
        pass
    try:
        mem = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            mem[k] = int(v.split()[0]) * 1024
        data["memTotal"] = mem["MemTotal"]
        data["memUsed"] = mem["MemTotal"] - mem.get("MemAvailable", 0)
        data["uptime"] = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, KeyError):
        pass
    du = shutil.disk_usage("/")
    data["diskTotal"], data["diskUsed"] = du.total, du.used
    addrs = []
    try:
        for iface in json.loads(run(["ip", "-j", "addr"]).stdout or "[]"):
            if iface.get("ifname") == "lo":
                continue
            for a in iface.get("addr_info", []):
                if a.get("family") == "inet":
                    addrs.append({"iface": iface["ifname"], "ip": a["local"], "mac": iface.get("address", "")})
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    data["addresses"] = addrs
    return data


def services() -> list[dict]:
    out = []
    for name, label in SERVICES.items():
        try:
            active = run(["systemctl", "is-active", name]).stdout.strip()
            enabled = run(["systemctl", "is-enabled", name]).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            active, enabled = "unbekannt", "unbekannt"
        installed = enabled not in ("", "not-found", "unbekannt")
        out.append({"name": name, "label": label, "active": active, "enabled": enabled, "installed": installed})
    return out


def users() -> list[dict]:
    result = []
    try:
        for line in Path("/etc/passwd").read_text().splitlines():
            parts = line.split(":")
            if len(parts) >= 7 and 1000 <= int(parts[2]) < 60000:
                result.append({"name": parts[0], "uid": int(parts[2]), "home": parts[5]})
    except (OSError, ValueError):
        pass
    return result


def snapshots() -> list[dict]:
    if not shutil.which("snapper"):
        return []
    try:
        res = run(["snapper", "--jsonout", "list"])
        data = json.loads(res.stdout or "{}")
        items = data.get("root", [])
        return [{"number": s.get("number"), "date": s.get("date", ""), "description": s.get("description", "")}
                for s in items if s.get("number")][-30:]
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def start_update() -> bool:
    if UPDATE_STATE["running"]:
        return False

    def worker():
        UPDATE_STATE.update(running=True, exit=None)
        with open(UPDATE_LOG, "w") as log:
            log.write(f"Update gestartet: {time.strftime('%d.%m.%Y %H:%M')}\n")
            log.flush()
            p = subprocess.run(["pacman", "-Syu", "--noconfirm"], stdout=log, stderr=subprocess.STDOUT)
        UPDATE_STATE.update(running=False, exit=p.returncode)

    threading.Thread(target=worker, daemon=True).start()
    return True


def update_log() -> str:
    try:
        return "\n".join(UPDATE_LOG.read_text(errors="replace").splitlines()[-40:])
    except OSError:
        return ""


# --------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = f"GlimraPanel/{__version__}"

    def log_message(self, fmt, *args):  # ruhiger als Standard
        sys.stderr.write(f"[panel] {self.address_string()} {fmt % args}\n")

    # Hilfsfunktionen
    def _json(self, data, code: int = 200, extra_headers: dict | None = None):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = min(int(self.headers.get("Content-Length", 0) or 0), 64_000)
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}

    def _authed(self) -> bool:
        jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        token = jar["glimra_session"].value if "glimra_session" in jar else ""
        exp = SESSIONS.get(token)
        if exp and exp > time.time():
            SESSIONS[token] = time.time() + SESSION_TTL
            return True
        SESSIONS.pop(token, None)
        return False

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin.split("://", 1)[-1] == self.headers.get("Host")

    # GET
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = (HERE / "static" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        m = re.fullmatch(r"/icons/([a-z0-9]+)\.svg", self.path)
        if m and (HERE / "static" / "icons" / f"{m.group(1)}.svg").is_file():
            body = (HERE / "static" / "icons" / f"{m.group(1)}.svg").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(body)
            return
        if not self.path.startswith("/api/"):
            return self._json({"error": "Nicht gefunden"}, 404)
        if not self._authed():
            return self._json({"error": "Nicht angemeldet"}, 401)
        routes = {
            "/api/status": status,
            "/api/services": services,
            "/api/users": users,
            "/api/snapshots": snapshots,
            "/api/update": lambda: {**UPDATE_STATE, "log": update_log()},
        }
        fn = routes.get(self.path)
        if fn is None:
            return self._json({"error": "Nicht gefunden"}, 404)
        self._json(fn())

    # POST
    def do_POST(self):
        if not self._same_origin():
            return self._json({"error": "Ungültige Herkunft"}, 403)
        data = self._body()
        if self.path == "/api/login":
            if check_password(str(data.get("password", ""))):
                token = secrets.token_urlsafe(32)
                SESSIONS[token] = time.time() + SESSION_TTL
                secure = "; Secure" if TLS["on"] else ""
                return self._json({"ok": True}, extra_headers={
                    "Set-Cookie": f"glimra_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL}{secure}"})
            time.sleep(1.5)  # bremst Passwort-Raten
            return self._json({"error": "Falsches Passwort"}, 403)
        if not self._authed():
            return self._json({"error": "Nicht angemeldet"}, 401)

        if self.path == "/api/logout":
            jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            if "glimra_session" in jar:
                SESSIONS.pop(jar["glimra_session"].value, None)
            return self._json({"ok": True})

        if self.path == "/api/services":
            name, action = data.get("name"), data.get("action")
            if name not in SERVICES or action not in SERVICE_ACTIONS:
                return self._json({"error": "Unbekannter Dienst oder Aktion"}, 400)
            if name == "NetworkManager" and action in ("stop", "disable"):
                return self._json({"error": "Das Netzwerk kann im Panel nicht abgeschaltet werden."}, 400)
            res = run(["systemctl", action, name], timeout=30)
            if res.returncode != 0:
                return self._json({"error": res.stderr.strip() or "Fehlgeschlagen"}, 500)
            return self._json({"ok": True})

        if self.path == "/api/users":
            name, pw = str(data.get("name", "")), str(data.get("password", ""))
            if not USERNAME_RE.match(name):
                return self._json({"error": "Ungültiger Benutzername (klein, ohne Leerzeichen)"}, 400)
            if len(pw) < 8:
                return self._json({"error": "Passwort muss mindestens 8 Zeichen haben"}, 400)
            res = run(["useradd", "-m", "-s", "/bin/bash", name])
            if res.returncode != 0:
                return self._json({"error": res.stderr.strip() or "Benutzer konnte nicht angelegt werden"}, 500)
            subprocess.run(["chpasswd"], input=f"{name}:{pw}", text=True)
            if shutil.which("smbpasswd"):
                subprocess.run(["smbpasswd", "-s", "-a", name], input=f"{pw}\n{pw}\n", text=True,
                               capture_output=True)
            return self._json({"ok": True})

        if self.path == "/api/users/delete":
            name = str(data.get("name", ""))
            if name not in {u["name"] for u in users()}:
                return self._json({"error": "Unbekannter Benutzer"}, 400)
            res = run(["userdel", "-r", name])
            if res.returncode != 0:
                return self._json({"error": res.stderr.strip() or "Löschen fehlgeschlagen"}, 500)
            return self._json({"ok": True})

        if self.path == "/api/update":
            return self._json({"ok": start_update()})

        if self.path == "/api/snapshots":
            desc = re.sub(r"[^\w äöüÄÖÜß.-]", "", str(data.get("description", "Panel")))[:60] or "Panel"
            if not shutil.which("snapper"):
                return self._json({"error": "Snapper ist nicht installiert"}, 400)
            res = run(["snapper", "create", "--description", desc], timeout=60)
            if res.returncode != 0:
                return self._json({"error": res.stderr.strip() or "Snapshot fehlgeschlagen"}, 500)
            return self._json({"ok": True})

        if self.path == "/api/power":
            action = data.get("action")
            if action not in ("reboot", "poweroff"):
                return self._json({"error": "Unbekannte Aktion"}, 400)
            threading.Timer(1.0, lambda: subprocess.run(["systemctl", action])).start()
            return self._json({"ok": True})

        self._json({"error": "Nicht gefunden"}, 404)


def make_cert(force: bool = False) -> bool:
    """Erstellt ein selbst signiertes Zertifikat für HTTPS (10 Jahre gültig)."""
    if CERT_FILE.exists() and KEY_FILE.exists() and not force:
        return True
    host = socket.gethostname()
    san = f"DNS:{host},DNS:{host}.local,DNS:localhost,IP:127.0.0.1"
    for a in status().get("addresses", []):
        san += f",IP:{a['ip']}"
    CERT_FILE.parent.mkdir(parents=True, exist_ok=True)
    res = run(["openssl", "req", "-x509", "-newkey", "rsa:3072", "-nodes", "-sha256", "-days", "3650",
               "-keyout", str(KEY_FILE), "-out", str(CERT_FILE), "-subj", f"/CN={host}/O=Glimra OS Server",
               "-addext", f"subjectAltName={san}"], timeout=120)
    if res.returncode != 0:
        print("Zertifikat konnte nicht erstellt werden:", res.stderr.strip(), file=sys.stderr)
        return False
    os.chmod(KEY_FILE, 0o600)
    return True


def cert_fingerprint() -> str:
    res = run(["openssl", "x509", "-in", str(CERT_FILE), "-noout", "-fingerprint", "-sha256"])
    return res.stdout.strip().split("=", 1)[-1] if res.returncode == 0 else ""


class RedirectHandler(BaseHTTPRequestHandler):
    """Leitet http://…:8080 auf https://…:8443 um."""
    https_port = 8443

    def log_message(self, *args):
        pass

    def do_GET(self):
        host = (self.headers.get("Host") or "localhost").split(":")[0]
        self.send_response(301)
        self.send_header("Location", f"https://{host}:{self.https_port}{self.path}")
        self.end_headers()

    do_POST = do_GET


def discovery_loop(port: int) -> None:
    """Antwortet der GlimraApp auf die Suche im Heimnetz (UDP 8766)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", 8766))
    except OSError:
        return
    while True:
        try:
            data, addr = s.recvfrom(256)
        except OSError:
            break
        if data.strip() == b"GLIMRA?":
            reply = {"glimra": 1, "type": "server", "name": socket.gethostname(), "port": port, "tls": TLS["on"]}
            s.sendto(json.dumps(reply).encode(), addr)


def main() -> int:
    ap = argparse.ArgumentParser(prog="glimra-panel")
    ap.add_argument("--port", type=int, default=int(os.environ.get("GLIMRA_PANEL_PORT", 0)) or None)
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--set-password", action="store_true", help="Panel-Passwort setzen")
    ap.add_argument("--make-cert", action="store_true", help="HTTPS-Zertifikat erstellen (falls keins da ist)")
    ap.add_argument("--fingerprint", action="store_true", help="Fingerabdruck des Zertifikats anzeigen")
    ap.add_argument("--no-tls", action="store_true", help="ohne HTTPS starten (nur zum Testen)")
    args = ap.parse_args()

    if args.make_cert:
        return 0 if make_cert() else 1
    if args.fingerprint:
        print(cert_fingerprint())
        return 0

    if args.set_password:
        pw = sys.stdin.readline().rstrip("\n") if not sys.stdin.isatty() else getpass.getpass("Neues Panel-Passwort: ")
        if len(pw) < 8:
            print("Das Passwort muss mindestens 8 Zeichen haben.", file=sys.stderr)
            return 1
        set_password(pw)
        print("Panel-Passwort gespeichert.")
        return 0

    if not CONF_FILE.exists():
        print("Kein Passwort gesetzt. Zuerst: glimra-panel --set-password", file=sys.stderr)
        return 1
    TLS["on"] = not args.no_tls and CERT_FILE.exists() and KEY_FILE.exists()
    port = args.port or (8443 if TLS["on"] else 8080)
    httpd = ThreadingHTTPServer((args.bind, port), Handler)
    if TLS["on"]:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(str(CERT_FILE), str(KEY_FILE))
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        if port != 8080:
            RedirectHandler.https_port = port
            try:
                redirect = ThreadingHTTPServer((args.bind, 8080), RedirectHandler)
                threading.Thread(target=redirect.serve_forever, kwargs={"poll_interval": 5}, daemon=True).start()
            except OSError:
                pass
    threading.Thread(target=discovery_loop, args=(port,), daemon=True).start()
    print(f"Glimra Panel läuft auf {'https' if TLS['on'] else 'http'}://0.0.0.0:{port}")
    httpd.serve_forever(poll_interval=5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
