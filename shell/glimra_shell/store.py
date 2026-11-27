"""Glimra Store und Glimra Update.

Store: Programme aus den Arch-Paketquellen (pacman) und von Flathub (Flatpak) suchen,
installieren und entfernen. Update: System und Flatpaks aktualisieren – vor jedem Update
legt snap-pac automatisch ein Backup an.
Installieren/Entfernen/Aktualisieren läuft über /usr/local/bin/glimra-store (root, über sudoers).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess

HELPER = "/usr/local/bin/glimra-store"
PKG_RE = re.compile(r"^(?:flatpak:[A-Za-z0-9._-]+|[a-z0-9@._+-]+)$")

# Empfohlene Programme (wie die Startseite im Microsoft Store)
FEATURED = [
    {"id": "firefox", "name": "Firefox", "desc": "Schneller, privater Browser", "cat": "Internet", "icon": "browser"},
    {"id": "chromium", "name": "Chromium", "desc": "Browser (Basis von Chrome)", "cat": "Internet", "icon": "browser"},
    {"id": "flatpak:com.discordapp.Discord", "name": "Discord", "desc": "Chat und Sprache mit Freunden", "cat": "Internet", "icon": "send"},
    {"id": "thunderbird", "name": "Thunderbird", "desc": "E-Mail und Kalender", "cat": "Büro", "icon": "mail"},
    {"id": "libreoffice-fresh", "name": "LibreOffice", "desc": "Texte, Tabellen, Präsentationen", "cat": "Büro", "icon": "file"},
    {"id": "keepassxc", "name": "KeePassXC", "desc": "Passwörter sicher speichern", "cat": "Büro", "icon": "key"},
    {"id": "vlc", "name": "VLC", "desc": "Spielt fast alle Videos und Musik", "cat": "Medien", "icon": "play"},
    {"id": "flatpak:com.spotify.Client", "name": "Spotify", "desc": "Musik streamen", "cat": "Medien", "icon": "volume"},
    {"id": "obs-studio", "name": "OBS Studio", "desc": "Bildschirm aufnehmen und streamen", "cat": "Medien", "icon": "camera"},
    {"id": "gimp", "name": "GIMP", "desc": "Bilder bearbeiten", "cat": "Kreativ", "icon": "image"},
    {"id": "krita", "name": "Krita", "desc": "Digital malen und zeichnen", "cat": "Kreativ", "icon": "palette"},
    {"id": "steam", "name": "Steam", "desc": "Spiele-Plattform", "cat": "Spiele", "icon": "game"},
    {"id": "flatpak:org.prismlauncher.PrismLauncher", "name": "Prism Launcher", "desc": "Minecraft mit Mods starten", "cat": "Spiele", "icon": "game"},
    {"id": "code", "name": "Code – OSS", "desc": "Programmieren (VS-Code-Variante)", "cat": "Entwicklung", "icon": "script"},
]


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def _root(cmd: list[str]) -> list[str]:
    return cmd if os.geteuid() == 0 else ["sudo", "-n", *cmd]


def installed_set() -> set[str]:
    names: set[str] = set()
    if shutil.which("pacman"):
        names |= set(_run(["pacman", "-Qq"], 20).stdout.split())
    if shutil.which("flatpak"):
        names |= {"flatpak:" + x for x in _run(["flatpak", "list", "--app", "--columns=application"], 20).stdout.split()}
    return names


def featured() -> list[dict]:
    inst = installed_set()
    return [{**f, "installed": f["id"] in inst} for f in FEATURED]


def parse_pacman_search(out: str) -> list[dict]:
    """Wandelt die Ausgabe von `pacman -Ss` in Einträge um."""
    results = []
    lines = out.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\S+)/(\S+) (\S+)(.*)$", line)
        if not m:
            continue
        desc = lines[i + 1].strip() if i + 1 < len(lines) and lines[i + 1].startswith(" ") else ""
        results.append({"id": m.group(2), "name": m.group(2), "desc": desc, "cat": m.group(1),
                        "icon": "apps", "installed": "[installiert" in m.group(4) or "[installed" in m.group(4)})
    return results


def search(query: str) -> list[dict]:
    q = query.strip()
    if len(q) < 2 or not re.fullmatch(r"[\w .+-]+", q):
        return []
    results: list[dict] = []
    low = q.lower()
    results += [f for f in featured() if low in f["name"].lower() or low in f["desc"].lower()]
    if shutil.which("pacman"):
        results += parse_pacman_search(_run(["pacman", "-Ss", q], 20).stdout)[:30]
    if shutil.which("flatpak"):
        inst = installed_set()
        out = _run(["flatpak", "search", "--columns=name,application,description", q], 30).stdout
        for line in out.splitlines()[:20]:
            parts = line.split("\t")
            if len(parts) >= 2 and "." in parts[1]:
                fid = "flatpak:" + parts[1]
                results.append({"id": fid, "name": parts[0], "desc": parts[2] if len(parts) > 2 else "",
                                "cat": "Flathub", "icon": "apps", "installed": fid in inst})
    seen, unique = set(), []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    return unique[:40]


def install(pkg: str) -> tuple[bool, str]:
    if not PKG_RE.match(pkg):
        return False, "Ungültiger Paketname."
    res = _run(_root([HELPER, "install", pkg]), 1800)
    return (True, "Installiert.") if res.returncode == 0 else (False, "Installation fehlgeschlagen (Internet?).")


def remove(pkg: str) -> tuple[bool, str]:
    if not PKG_RE.match(pkg):
        return False, "Ungültiger Paketname."
    res = _run(_root([HELPER, "remove", pkg]), 600)
    return (True, "Entfernt.") if res.returncode == 0 else (False, "Entfernen fehlgeschlagen.")


# ------------------------------------------------------------------ Updates
def check_updates() -> list[dict]:
    """Verfügbare Updates (ohne root, über checkupdates aus pacman-contrib)."""
    ups: list[dict] = []
    if shutil.which("checkupdates"):
        for line in _run(["checkupdates"], 120).stdout.splitlines():
            m = re.match(r"(\S+) (\S+) -> (\S+)", line)
            if m:
                ups.append({"name": m.group(1), "old": m.group(2), "new": m.group(3)})
    if shutil.which("flatpak"):
        out = _run(["flatpak", "remote-ls", "--updates", "--app", "--columns=application,version"], 60).stdout
        for line in out.splitlines():
            parts = line.split("\t")
            if parts and "." in parts[0]:
                ups.append({"name": parts[0], "old": "", "new": parts[1] if len(parts) > 1 else ""})
    return ups


def run_updates(progress) -> tuple[bool, str]:
    cmd = _root([HELPER, "update"])
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except OSError as e:
        return False, str(e)
    for line in p.stdout:  # type: ignore[union-attr]
        line = line.strip()
        if line:
            progress(line[:120])
    p.wait()
    if p.returncode == 0:
        return True, "Alles aktuell. Ein Backup des alten Stands wurde angelegt."
    return False, "Update fehlgeschlagen – siehe Hilfe → Systembericht."
