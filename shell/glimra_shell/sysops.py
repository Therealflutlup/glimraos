"""Systemfunktionen der Glimra Shell: Sicherheit, Backups, virtuelle PCs, Umzug, Hilfe."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

HOME = Path.home()


def _root_cmd(cmd: list[str]) -> list[str]:
    """Systemhelfer laufen als root – ohne Passwort erlaubt über /etc/sudoers.d/20-glimra."""
    return cmd if os.geteuid() == 0 else ["sudo", "-n", *cmd]


def run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


# ------------------------------------------------------------------ Sicherheit
def security_status() -> dict:
    res = run(_root_cmd(["/usr/local/bin/glimra-security", "status"]), timeout=10)
    try:
        data = json.loads(res.stdout)
    except ValueError:
        data = {"firewall": "unbekannt", "db": ""}
    data["clamav"] = bool(shutil.which("clamscan"))
    return data


def set_firewall(on: bool) -> tuple[bool, str]:
    res = run(_root_cmd(["/usr/local/bin/glimra-security", "firewall", "on" if on else "off"]), timeout=60)
    if res.returncode == 0:
        return True, "Firewall ist an." if on else "Firewall ist aus."
    return False, "Firewall konnte nicht geändert werden."


def update_virus_db() -> tuple[bool, str]:
    res = run(_root_cmd(["/usr/local/bin/glimra-security", "update"]), timeout=900)
    return (True, "Virendatenbank ist aktuell.") if res.returncode == 0 else \
        (False, "Update der Virendatenbank fehlgeschlagen (Internet?).")


def virus_scan(path: str) -> tuple[bool, str]:
    if not shutil.which("clamscan"):
        return False, "ClamAV ist nicht installiert."
    target = Path(path).expanduser()
    res = run(["clamscan", "-r", "-i", "--max-filesize=200M", str(target)], timeout=7200)
    infected = re.search(r"Infected files:\s*(\d+)", res.stdout)
    scanned = re.search(r"Scanned files:\s*(\d+)", res.stdout)
    if res.returncode == 2 and not infected:
        if "database" in (res.stderr + res.stdout).lower():
            return False, "Keine Virendatenbank – zuerst „Datenbank aktualisieren“."
        return False, "Scan fehlgeschlagen."
    n = int(infected.group(1)) if infected else 0
    s = scanned.group(1) if scanned else "?"
    if n == 0:
        return True, f"Keine Bedrohungen gefunden ({s} Dateien geprüft)."
    hits = [line.split(":")[0] for line in res.stdout.splitlines() if line.endswith("FOUND")][:5]
    return False, f"{n} verdächtige Datei(en): " + ", ".join(Path(h).name for h in hits)


# ------------------------------------------------------------------ Backups
def snapshots() -> list[dict]:
    res = run(_root_cmd(["/usr/local/bin/glimra-backup", "list"]), timeout=20)
    try:
        items = json.loads(res.stdout or "[]")
    except ValueError:
        return []
    return list(reversed(items))[:40]


def create_snapshot(desc: str) -> tuple[bool, str]:
    desc = re.sub(r"[^\w äöüÄÖÜß.-]", "", desc)[:60] or "Manuell"
    res = run(_root_cmd(["/usr/local/bin/glimra-backup", "create", desc]), timeout=120)
    return (True, "Backup erstellt.") if res.returncode == 0 else (False, res.stderr.strip() or "Backup fehlgeschlagen.")


def restore_snapshot(number: int) -> tuple[bool, str]:
    res = run(_root_cmd(["/usr/local/bin/glimra-backup", "restore", str(int(number))]), timeout=300)
    if res.returncode == 0:
        return True, "Backup wird beim nächsten Neustart geladen. Bitte jetzt neu starten."
    return False, res.stderr.strip() or "Wiederherstellen fehlgeschlagen."


# ------------------------------------------------------------------ Virtuelle PCs
VIRSH = ["virsh", "-c", "qemu:///system"]


def vm_available() -> bool:
    return bool(shutil.which("virsh") and shutil.which("virt-install"))


def vm_list() -> list[dict]:
    if not vm_available():
        return []
    res = run(VIRSH + ["list", "--all"], timeout=15)
    vms = []
    for line in res.stdout.splitlines()[2:]:
        parts = line.split(None, 2)
        if len(parts) >= 3:
            vms.append({"name": parts[1], "state": parts[2].strip()})
    return vms


def iso_files() -> list[str]:
    found = []
    for d in (HOME / "Downloads", HOME / "ISOs", HOME):
        if d.is_dir():
            found += [str(p) for p in d.glob("*.iso")]
    return sorted(set(found))


def vm_create(name: str, iso: str, ram_mb: int, disk_gb: int) -> tuple[bool, str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name):
        return False, "Name nur mit Buchstaben, Zahlen, - und _."
    if not Path(iso).is_file():
        return False, "ISO-Datei nicht gefunden."
    cmd = ["virt-install", "--connect", "qemu:///system", "--name", name,
           "--memory", str(max(512, min(ram_mb, 65536))), "--vcpus", "2",
           "--disk", f"size={max(8, min(disk_gb, 2000))}", "--cdrom", iso,
           "--osinfo", "detect=on,require=off", "--graphics", "spice", "--noautoconsole"]
    res = run(cmd, timeout=300)
    if res.returncode == 0:
        return True, f"Virtueller PC „{name}“ wurde erstellt und gestartet."
    return False, (res.stderr.strip().splitlines() or ["Erstellen fehlgeschlagen."])[-1]


def vm_action(name: str, action: str, launcher) -> tuple[bool, str]:
    cmds = {"start": ["start", name], "shutdown": ["shutdown", name], "destroy": ["destroy", name],
            "delete": ["undefine", name, "--remove-all-storage", "--nvram"]}
    if action == "view":
        launcher(f"virt-viewer --connect qemu:///system --wait {name}")
        return True, ""
    if action not in cmds:
        return False, "Unbekannte Aktion"
    if action == "delete":
        run(VIRSH + ["destroy", name], timeout=30)
    res = run(VIRSH + cmds[action], timeout=60)
    texts = {"start": "gestartet", "shutdown": "wird heruntergefahren", "destroy": "ausgeschaltet",
             "delete": "gelöscht"}
    if res.returncode == 0:
        return True, f"„{name}“ {texts[action]}."
    return False, res.stderr.strip() or "Fehlgeschlagen."


# ------------------------------------------------------------------ Umzug
# Ordnernamen von Windows/Linux (englisch und deutsch) -> Glimra-Ordner
FOLDER_MAP = {
    "Dokumente": ["Dokumente", "Documents", "Eigene Dateien"],
    "Bilder": ["Bilder", "Pictures"],
    "Musik": ["Musik", "Music"],
    "Videos": ["Videos", "Movies"],
    "Desktop": ["Desktop", "Schreibtisch"],
    "Downloads": ["Downloads"],
    "Lesezeichen": ["Lesezeichen"],
    "Hintergrund": ["Hintergrund"],
}


def transfer_sources() -> list[dict]:
    """Findet Umzugspakete (vom Setup-Manager) und alte Benutzerordner auf USB-Sticks."""
    candidates = [HOME / "Umzug"]
    user = os.environ.get("USER", "")
    for base in (Path("/run/media") / user, Path("/media"), Path("/mnt")):
        if base.is_dir():
            for drive in base.iterdir():
                candidates += [drive / "GlimraUmzug", drive]
                home = drive / "home"
                if home.is_dir():
                    candidates += [p for p in home.iterdir() if p.is_dir()]
                users = drive / "Users"
                if users.is_dir():
                    candidates += [p for p in users.iterdir() if p.is_dir() and p.name not in ("Public", "Default", "All Users")]
    result, seen = [], set()
    for c in candidates:
        try:
            if not c.is_dir() or c.resolve() in seen:
                continue
        except OSError:
            continue
        cats = [cat for cat, names in FOLDER_MAP.items() if any((c / n).is_dir() for n in names)]
        if cats:
            seen.add(c.resolve())
            label = "Umzugspaket" if c.name in ("GlimraUmzug", "Umzug") else "Benutzerordner"
            result.append({"path": str(c), "label": f"{label}: {c}", "categories": cats})
    return result


def import_from(source: str, categories: list[str], progress) -> tuple[bool, str]:
    src = Path(source)
    copied = 0
    for cat in categories:
        names = FOLDER_MAP.get(cat, [])
        folder = next((src / n for n in names if (src / n).is_dir()), None)
        if folder is None:
            continue
        dest = HOME / ("Dokumente/Lesezeichen" if cat == "Lesezeichen" else
                       "Bilder/Hintergrund" if cat == "Hintergrund" else cat)
        progress(f"Kopiere {cat} …")
        for f in folder.rglob("*"):
            if f.is_file():
                target = dest / f.relative_to(folder)
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        shutil.copy2(f, target)
                        copied += 1
                except OSError:
                    continue
    return True, f"Umzug fertig: {copied} Dateien übernommen."


def wallpaper_images() -> list[str]:
    out = []
    for d in (HOME / "Bilder" / "Hintergrund", HOME / "Bilder", HOME / "Pictures"):
        if d.is_dir():
            out += [str(p) for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    return sorted(set(out))[:24]


# ------------------------------------------------------------------ Hilfe
def system_report(shell_log: Path) -> str:
    lines = [f"Glimra OS Systembericht – {time.strftime('%d.%m.%Y %H:%M')}", "=" * 50]

    def section(title: str, cmd: list[str]) -> None:
        res = run(cmd, timeout=15)
        lines.extend(["", f"## {title}", (res.stdout or res.stderr).strip()[:6000]])

    try:
        lines += ["", "## System", Path("/etc/os-release").read_text().strip()]
    except OSError:
        lines += ["", "## System", platform.platform()]
    section("Kernel", ["uname", "-a"])
    section("Festplatten", ["lsblk", "-o", "NAME,SIZE,FSTYPE,MOUNTPOINTS"])
    section("Netzwerk", ["ip", "-br", "addr"])
    section("Grafik", ["sh", "-c", "ls /dev/dri 2>&1; cat /proc/driver/nvidia/version 2>/dev/null"])
    section("Fehler seit dem Start", ["journalctl", "-b", "-p", "3", "-n", "60", "--no-pager"])
    try:
        lines += ["", "## Glimra Shell Protokoll", shell_log.read_text(errors="replace")[-6000:]]
    except OSError:
        pass
    target = HOME / "Desktop" / "glimra-systembericht.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return str(target)
