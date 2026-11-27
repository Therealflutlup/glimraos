"""Glimra Setup-Manager – Logik ohne Oberfläche (testbar auch unter Linux).

PC prüfen, Glimra OS herunterladen, Rufus holen, Daten für den Umzug sammeln,
in einen Ordner/USB-Stick kopieren oder über das Netzwerk an Glimra OS senden.
"""

from __future__ import annotations

import http.client
import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import __version__

REPO = os.environ.get("GLIMRA_REPO", "therealflutlup/glimraos")   # GitHub-Repo mit den Releases
UA = {"User-Agent": f"GlimraSetup/{__version__}"}
IS_WIN = sys.platform == "win32"

CATEGORIES = ["Dokumente", "Bilder", "Musik", "Videos", "Desktop", "Downloads", "Lesezeichen", "Hintergrund"]


class Cancelled(Exception):
    pass


# ------------------------------------------------------------------ Windows-Ordner
_KNOWN = {  # Known-Folder-IDs (berücksichtigt auch OneDrive-Umleitungen)
    "Dokumente": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "Bilder": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "Musik": "{4BD8D571-6D19-48D3-BE97-422220080E43}",
    "Videos": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
    "Desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "Downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
}
_FALLBACK = {"Dokumente": "Documents", "Bilder": "Pictures", "Musik": "Music",
             "Videos": "Videos", "Desktop": "Desktop", "Downloads": "Downloads"}


def known_folder(cat: str) -> Path:
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes
            import uuid

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            u = uuid.UUID(_KNOWN[cat])
            g = GUID(u.fields[0], u.fields[1], u.fields[2], (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            ptr = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(ptr)) == 0:
                path = ptr.value
                ctypes.windll.ole32.CoTaskMemFree(ptr)
                return Path(path)
        except Exception:  # noqa: BLE001
            pass
    return Path.home() / _FALLBACK[cat]


# ------------------------------------------------------------------ PC prüfen
def system_check() -> list[tuple[str, bool, str]]:
    """Liste von (Prüfung, ok, Hinweis)."""
    checks = []
    bits64 = platform.machine().lower() in ("amd64", "x86_64")
    checks.append(("64-Bit-Prozessor", bits64, platform.machine()))

    ram_gb = 0.0
    if IS_WIN:
        import ctypes

        class MEM(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MEM()
        m.dwLength = ctypes.sizeof(MEM)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        ram_gb = m.ullTotalPhys / 1024 ** 3
    else:
        try:
            ram_gb = int(Path("/proc/meminfo").read_text().split()[1]) / 1024 ** 2
        except (OSError, ValueError, IndexError):
            pass
    checks.append(("Arbeitsspeicher (mind. 4 GB)", ram_gb >= 3.8, f"{ram_gb:.1f} GB"))

    free = shutil.disk_usage(Path.home().anchor or "/").free / 1024 ** 3
    checks.append(("Freier Speicher für ISO (mind. 4 GB)", free >= 4, f"{free:.0f} GB frei"))

    uefi, secure = None, None
    if IS_WIN:
        import ctypes
        ctypes.windll.kernel32.GetFirmwareEnvironmentVariableW("", "{00000000-0000-0000-0000-000000000000}", None, 0)
        err = ctypes.windll.kernel32.GetLastError()
        uefi = err != 1  # 1 = ERROR_INVALID_FUNCTION -> altes BIOS
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\SecureBoot\State") as k:
                secure = winreg.QueryValueEx(k, "UEFISecureBootEnabled")[0] == 1
        except OSError:
            secure = False
    else:
        uefi = Path("/sys/firmware/efi").exists()
    checks.append(("UEFI-Firmware", bool(uefi), "UEFI" if uefi else "altes BIOS – Glimra OS braucht UEFI"))
    if secure is not None:
        checks.append(("Secure Boot aus", not secure,
                       "Secure Boot ist an – im BIOS/UEFI ausschalten" if secure else "aus"))
    return checks


# ------------------------------------------------------------------ Downloads
def _get_json(url: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.loads(r.read())


def latest_iso(edition: str) -> tuple[str, str, int]:
    """(Version, Download-URL, Größe) der neuesten Glimra-OS-ISO aus den GitHub-Releases."""
    rel = _get_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    for a in rel.get("assets", []):
        if a["name"].startswith(f"glimraos-{edition}") and a["name"].endswith(".iso"):
            return rel.get("tag_name", "?"), a["browser_download_url"], a.get("size", 0)
    raise RuntimeError(f"Im neuesten Release gibt es keine {edition}-ISO.")


def rufus_url() -> str:
    rel = _get_json("https://api.github.com/repos/pbatard/rufus/releases/latest")
    for a in rel.get("assets", []):
        n = a["name"].lower()
        if n.endswith("p.exe") and "arm" not in n:   # portable Version
            return a["browser_download_url"]
    for a in rel.get("assets", []):
        if a["name"].lower().endswith(".exe") and "arm" not in a["name"].lower():
            return a["browser_download_url"]
    raise RuntimeError("Rufus-Download nicht gefunden.")


def download(url: str, dest: Path, progress=None, cancel=None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length", 0) or 0)
        done = 0
        while True:
            if cancel and cancel():
                raise Cancelled()
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    tmp.replace(dest)
    return dest


# ------------------------------------------------------------------ Lesezeichen / Hintergrund
def _netscape(items: list[tuple[str, str]], title: str) -> str:
    import html
    rows = "\n".join(f'    <DT><A HREF="{html.escape(u)}">{html.escape(t or u)}</A>' for t, u in items)
    return ("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n"
            f"<TITLE>{title}</TITLE>\n<H1>{title}</H1>\n<DL><p>\n{rows}\n</DL><p>\n")


def export_bookmarks(out_dir: Path) -> list[Path]:
    """Exportiert Lesezeichen aus Chrome, Edge und Firefox als HTML (in jeden Browser importierbar)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    chromium = {"Chrome": local / "Google/Chrome/User Data/Default/Bookmarks",
                "Edge": local / "Microsoft/Edge/User Data/Default/Bookmarks",
                "Brave": local / "BraveSoftware/Brave-Browser/User Data/Default/Bookmarks"}
    for name, f in chromium.items():
        if not f.exists():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        items: list[tuple[str, str]] = []

        def walk(node, items=items):
            if node.get("type") == "url":
                items.append((node.get("name", ""), node.get("url", "")))
            for c in node.get("children", []):
                walk(c, items)
        for root in data.get("roots", {}).values():
            if isinstance(root, dict):
                walk(root)
        if items:
            p = out_dir / f"{name}-Lesezeichen.html"
            p.write_text(_netscape(items, f"{name} Lesezeichen"), encoding="utf-8")
            results.append(p)
    ff = roaming / "Mozilla/Firefox/Profiles"
    if ff.is_dir():
        for prof in ff.iterdir():
            places = prof / "places.sqlite"
            if not places.exists():
                continue
            tmp = Path(tempfile.mkdtemp()) / "places.sqlite"
            try:
                shutil.copy2(places, tmp)
                con = sqlite3.connect(tmp)
                rows = con.execute("SELECT b.title, p.url FROM moz_bookmarks b JOIN moz_places p ON b.fk = p.id "
                                   "WHERE b.type = 1 AND p.url LIKE 'http%'").fetchall()
                con.close()
            except (OSError, sqlite3.Error):
                continue
            if rows:
                p = out_dir / f"Firefox-{prof.name.split('.')[-1]}-Lesezeichen.html"
                p.write_text(_netscape(rows, "Firefox Lesezeichen"), encoding="utf-8")
                results.append(p)
    return results


def wallpaper_path() -> Path | None:
    if not IS_WIN:
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as k:
            p = Path(winreg.QueryValueEx(k, "WallPaper")[0])
            return p if p.is_file() else None
    except OSError:
        return None


# ------------------------------------------------------------------ Umzug
def collect(categories: list[str], work: Path) -> list[tuple[Path, str]]:
    """Alle Dateien der Kategorien als (Quelle, Zielpfad wie 'Bilder/Urlaub/a.jpg')."""
    files: list[tuple[Path, str]] = []
    for cat in categories:
        if cat == "Lesezeichen":
            for p in export_bookmarks(work / "Lesezeichen"):
                files.append((p, f"Lesezeichen/{p.name}"))
            continue
        if cat == "Hintergrund":
            wp = wallpaper_path()
            if wp:
                files.append((wp, f"Hintergrund/{wp.name}"))
            continue
        base = known_folder(cat)
        if not base.is_dir():
            continue
        for root, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("$recycle.bin", "node_modules")]
            for n in names:
                if n.lower() in ("desktop.ini", "thumbs.db") or n.startswith("~$"):
                    continue
                src = Path(root) / n
                rel = src.relative_to(base).as_posix()
                files.append((src, f"{cat}/{rel}"))
    return files


def category_sizes() -> dict[str, tuple[int, int]]:
    """Anzahl Dateien und Größe je Ordner (für die Anzeige)."""
    out = {}
    for cat in _KNOWN:
        base = known_folder(cat)
        n = size = 0
        if base.is_dir():
            for root, _, names in os.walk(base):
                for name in names:
                    try:
                        size += (Path(root) / name).stat().st_size
                        n += 1
                    except OSError:
                        pass
        out[cat] = (n, size)
    return out


def copy_to_folder(files, target: Path, progress=None, cancel=None) -> int:
    dest_root = target / "GlimraUmzug"
    total = sum(_size(f) for f, _ in files) or 1
    done = copied = 0
    for src, rel in files:
        if cancel and cancel():
            raise Cancelled()
        dst = dest_root / rel
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        except OSError:
            pass
        done += _size(src)
        if progress:
            progress(done, total, rel)
    (dest_root / "glimra-umzug.json").write_text(json.dumps(
        {"glimraUmzug": 1, "von": platform.node(), "datum": time.strftime("%d.%m.%Y %H:%M"), "dateien": copied}, indent=2))
    return copied


def send_to_glimra(files, ip: str, code: str, progress=None, cancel=None) -> int:
    host = ip.strip()
    port = 8765
    if ":" in host:
        host, p = host.rsplit(":", 1)
        port = int(p)
    check_glimra(host, port, code)
    total = sum(_size(f) for f, _ in files) or 1
    done = sent = 0
    for src, rel in files:
        if cancel and cancel():
            raise Cancelled()
        size = _size(src)
        conn = http.client.HTTPConnection(host, port, timeout=30)
        try:
            conn.putrequest("POST", "/transfer")
            conn.putheader("X-Glimra-Code", code.strip())
            conn.putheader("X-Glimra-Path", urllib.parse.quote(rel))
            conn.putheader("Content-Length", str(size))
            conn.putheader("Content-Type", "application/octet-stream")
            conn.endheaders()
            with open(src, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    conn.send(chunk)
            resp = conn.getresponse()
            resp.read()
            if resp.status == 403:
                raise PermissionError("Falscher Umzugs-Code – schau in Glimra OS in der App „Umzug“ nach.")
            if resp.status == 200:
                sent += 1
        except (ConnectionError, OSError) as e:
            if isinstance(e, PermissionError):
                raise
            if sent == 0 and done == 0:
                raise ConnectionError(f"Glimra OS unter {host} nicht erreichbar. Ist die App „Umzug“ offen?") from e
        finally:
            conn.close()
        done += size
        if progress:
            progress(done, total, rel)
    return sent


def check_glimra(host: str, port: int, code: str) -> str:
    """Prüft Erreichbarkeit und Umzugs-Code, bevor Dateien gesendet werden."""
    conn = http.client.HTTPConnection(host, port, timeout=8)
    try:
        conn.request("GET", "/transfer-check", headers={"X-Glimra-Code": code.strip()})
        resp = conn.getresponse()
        data = json.loads(resp.read() or b"{}")
    except (OSError, ValueError) as e:
        raise ConnectionError(f"Glimra OS unter {host} nicht erreichbar. Ist die App „Umzug“ offen und der Empfang an?") from e
    finally:
        conn.close()
    if resp.status == 403:
        raise PermissionError("Falscher Umzugs-Code – schau in Glimra OS in der App „Umzug“ nach.")
    if resp.status != 200:
        raise ConnectionError("Glimra OS hat die Verbindung abgelehnt.")
    return data.get("name", host)


def _size(p: Path) -> int:
    try:
        return p.stat().st_size
    except OSError:
        return 0


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
