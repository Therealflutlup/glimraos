"""Grafischer Installer: Glimra OS vom USB-Stick fest auf eine Festplatte installieren.

Die eigentliche Arbeit macht /usr/local/bin/glimra-install --auto. Dieses Modul
findet die Festplatten, prüft die Eingaben und liest den Fortschritt mit.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

INSTALL_TOOL = "/usr/local/bin/glimra-install"
MIN_SIZE = 20 * 1000**3          # 20 GB
STEPS = 6

HOST_RE = re.compile(r"^[a-zA-Z0-9-]{1,63}$")
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")

# Vorschau unter Windows/ohne Live-System: Beispiel-Festplatten, nichts wird verändert
_DEMO_DISKS = [
    {"path": "/dev/nvme0n1", "size": 512110190592, "model": "Samsung SSD 980", "tran": "nvme", "removable": False},
    {"path": "/dev/sda", "size": 1000204886016, "model": "WDC WD10EZEX", "tran": "sata", "removable": False},
    {"path": "/dev/sdc", "size": 15518924800, "model": "SanDisk Ultra", "tran": "usb", "removable": True},
]


def is_live() -> bool:
    """True, wenn Glimra OS gerade vom USB-Stick / von der ISO läuft."""
    if os.environ.get("GLIMRA_FAKE_LIVE") == "1":
        return True
    return Path("/run/archiso").is_dir()


def edition() -> str:
    try:
        return Path("/etc/glimra/edition").read_text(encoding="utf-8").strip() or "desktop"
    except OSError:
        return "desktop"


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1000 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB", "MB") else f"{n:.1f} {unit}".replace(".", ",")
        n /= 1000
    return f"{n} TB"


def _boot_disk() -> str:
    """Gerät des USB-Sticks, von dem das Live-System läuft (darauf nie installieren)."""
    try:
        src = subprocess.run(["findmnt", "-no", "SOURCE", "/run/archiso/bootmnt"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        if not src:
            return ""
        parent = subprocess.run(["lsblk", "-no", "PKNAME", src],
                                capture_output=True, text=True, timeout=5).stdout.split()
        return "/dev/" + parent[0] if parent else src
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_lsblk(data: dict, boot_disk: str = "") -> list[dict]:
    """lsblk -J Ausgabe → Liste geeigneter Festplatten für die Oberfläche."""
    disks = []
    for d in data.get("blockdevices", []):
        if d.get("type") != "disk":
            continue
        path = d.get("path") or "/dev/" + d.get("name", "")
        name = d.get("name", "")
        if name.startswith(("loop", "sr", "zram", "ram")):
            continue
        size = int(d.get("size") or 0)
        tran = (d.get("tran") or "").lower()
        removable = bool(d.get("rm")) or tran == "usb"
        disks.append({
            "path": path,
            "size": size,
            "model": (d.get("model") or "").strip() or "Festplatte",
            "tran": tran,
            "removable": removable,
            "isBoot": path == boot_disk,
        })
    return disks


def decorate(disks: list[dict]) -> list[dict]:
    out = []
    for d in disks:
        kind = {"nvme": "NVMe-SSD", "sata": "SATA", "usb": "USB", "mmc": "Speicherkarte"}.get(d["tran"], "Laufwerk")
        problem = ""
        if d.get("isBoot"):
            problem = "Von diesem Stick läuft Glimra OS gerade"
        elif d["size"] < MIN_SIZE:
            problem = "Zu klein (mindestens 20 GB)"
        out.append({**d, "sizeText": human_size(d["size"]), "kind": kind,
                    "usable": problem == "", "problem": problem,
                    "isBoot": bool(d.get("isBoot"))})
    # interne Festplatten zuerst, dann nach Größe
    out.sort(key=lambda x: (not x["usable"], x["removable"], -x["size"]))
    return out


def list_disks() -> list[dict]:
    if not sys.platform.startswith("linux") or not Path(INSTALL_TOOL).exists():
        return decorate([dict(d, isBoot=False) for d in _DEMO_DISKS])
    try:
        raw = subprocess.run(["lsblk", "-J", "-b", "-d", "-o", "NAME,PATH,SIZE,MODEL,TYPE,TRAN,RM"],
                             capture_output=True, text=True, timeout=10).stdout
        return decorate(parse_lsblk(json.loads(raw or "{}"), _boot_disk()))
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def has_internet(host: str = "archlinux.org", port: int = 443, timeout: float = 4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def validate(host: str, user: str, pw1: str, pw2: str, panel_pw: str = "", ed: str = "desktop") -> str:
    """Leerer Text = alles in Ordnung, sonst eine verständliche Fehlermeldung."""
    if not HOST_RE.match(host or ""):
        return "Rechnername: nur Buchstaben, Zahlen und Bindestrich (z. B. leon-pc)."
    if not USER_RE.match(user or ""):
        return "Benutzername: klein geschrieben, ohne Leerzeichen (z. B. leon)."
    if not pw1:
        return "Bitte ein Passwort eingeben."
    if "\n" in pw1 or "\r" in pw1:
        return "Das Passwort darf keinen Zeilenumbruch enthalten."
    if pw1 != pw2:
        return "Die beiden Passwörter sind nicht gleich."
    if ed == "server" and len(panel_pw or "") < 8:
        return "Das Panel-Passwort braucht mindestens 8 Zeichen."
    return ""


def parse_line(line: str):
    """Eine Ausgabezeile von glimra-install --auto → (Art, Daten)."""
    line = line.rstrip("\n")
    if line.startswith("@@STEP "):
        parts = line.split(" ", 3)
        try:
            return "step", (int(parts[1]), int(parts[2]), parts[3] if len(parts) > 3 else "")
        except (ValueError, IndexError):
            return "log", line
    if line.startswith("@@ERROR"):
        return "error", line[7:].strip() or "Unbekannter Fehler"
    if line.strip() == "@@DONE":
        return "done", ""
    return "log", line


def run_install(disk: str, host: str, user: str, password: str, panel_pw: str,
                on_step, on_log, log_file: Path | None = None) -> tuple[bool, str]:
    """Startet die Installation und meldet jeden Schritt. Blockiert bis zum Ende."""
    if not sys.platform.startswith("linux") or not Path(INSTALL_TOOL).exists():
        return False, "Die Installation geht nur im Glimra-OS-Live-System (vom USB-Stick)."
    cmd = [INSTALL_TOOL, "--auto"]
    if os.geteuid() != 0:
        cmd = ["sudo", "-n"] + cmd
    env = dict(os.environ, LANG="de_DE.UTF-8", TERM="dumb")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, env=env)
    assert proc.stdin and proc.stdout
    proc.stdin.write("\n".join([disk, host, user, password, panel_pw]) + "\n")
    proc.stdin.close()
    log = open(log_file, "w", encoding="utf-8") if log_file else None
    error, done = "", False
    try:
        for line in proc.stdout:
            kind, data = parse_line(line)
            if log and kind != "step":
                log.write(line)
            if kind == "step":
                on_step(*data)
            elif kind == "error":
                error = data
            elif kind == "done":
                done = True
            elif data.strip():
                on_log(data.strip()[:200])
    finally:
        if log:
            log.close()
    code = proc.wait()
    if done and code == 0:
        return True, "Glimra OS ist installiert."
    return False, error or f"Die Installation ist abgebrochen (Code {code})."
