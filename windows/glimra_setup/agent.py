"""Glimra Agent für Windows: Der Windows-PC lässt sich mit der GlimraApp (Android) steuern.

Spricht dasselbe Protokoll wie Glimra OS (HTTP 8765, Suche über UDP 8766, Kopplung mit
6-stelligem Code) und kann zusätzlich: Bildschirm ansehen, laufende Programme sehen und
beenden, Nachricht als Fenster zeigen, Benutzer abmelden, Ruhezustand, Programme starten.
Für die spätere Anbindung an eine Domäne (z. B. heim.lan mit Samba AD) meldet der Agent
Domäne und angemeldete Benutzer mit.

  GlimraSetup.exe            Setup-Manager mit Seite „Handy verbinden“
  GlimraSetup.exe --agent    nur der Agent, unsichtbar im Hintergrund (Autostart)
"""

from __future__ import annotations

import csv
import getpass
import io
import os
import platform
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import webbrowser
import zlib
from pathlib import Path

from glimra_shell.remote import HTTP_PORT, RemoteServer

IS_WIN = sys.platform == "win32"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Glimra"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "GlimraAgent"
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

# Programme, die das Handy starten darf (feste Liste – keine beliebigen Befehle)
LAUNCH = {
    "explorer": ("Explorer", ["explorer.exe"]),
    "browser": ("Browser", ["cmd", "/c", "start", "", "https://"]),
    "taskmgr": ("Task-Manager", ["taskmgr.exe"]),
    "notepad": ("Editor", ["notepad.exe"]),
    "calc": ("Rechner", ["calc.exe"]),
    "settings": ("Einstellungen", ["cmd", "/c", "start", "", "ms-settings:"]),
}
# Diese Prozesse werden nie beendet (würde Windows abstürzen lassen oder abmelden)
PROTECTED = {"system", "idle", "registry", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
             "services.exe", "lsass.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe", "memcompression",
             "glimrasetup.exe"}

FEATURES = ["lock", "clipboard", "notify", "open", "power", "volume", "media", "upload",
            "screen", "processes", "kill", "message", "logoff", "hibernate", "launch", "users"]


def _run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              creationflags=NO_WINDOW if IS_WIN else 0, encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}".replace(".", ",") if unit in ("GB", "TB") else f"{n:.0f} {unit}"
        n /= 1024
    return str(n)


def duration(seconds: float) -> str:
    m = int(seconds // 60)
    d, h, m = m // 1440, (m // 60) % 24, m % 60
    return (f"{d} T. " if d else "") + f"{h} Std. {m} Min."


# ------------------------------------------------------------------ Auswerten (auch unter Linux testbar)
def parse_tasklist(text: str) -> list[dict]:
    """tasklist /fo csv /nh → [{name, pid, session, mem}] nach Speicher sortiert."""
    procs = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 5:
            continue
        try:
            pid = int(row[1])
        except ValueError:
            continue
        mem_kb = int("".join(ch for ch in row[4] if ch.isdigit()) or 0)
        procs.append({"name": row[0], "pid": pid, "session": row[2], "mem": mem_kb * 1024,
                      "memText": human(mem_kb * 1024), "protected": row[0].lower() in PROTECTED})
    return sorted(procs, key=lambda p: -p["mem"])


def parse_quser(text: str) -> list[dict]:
    """query user → [{user, session, state, since}] (der eigene Eintrag beginnt mit '>')."""
    users = []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    for ln in lines[1:]:
        current = ln.startswith(">")
        parts = ln.lstrip(">").split()
        if len(parts) < 4:
            continue
        name = parts[0]
        # Getrennte Sitzungen haben keinen Sitzungsnamen: USER ID STATE ...
        if parts[1].isdigit():
            sid, state, rest = parts[1], parts[2], parts[4:]
        else:
            sid, state, rest = parts[2], parts[3], parts[5:]
        users.append({"user": name, "session": sid, "state": "aktiv" if state.lower() in ("active", "aktiv") else "getrennt",
                      "since": " ".join(rest[-2:]) if len(rest) >= 2 else "", "current": current})
    return users


def png_encode(width: int, height: int, rgb_rows: list[bytes]) -> bytes:
    """Minimaler PNG-Encoder (RGB, 8 Bit) – keine Zusatzpakete nötig."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + row for row in rgb_rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def bgra_to_rows(buf: bytes, width: int, height: int) -> list[bytes]:
    rows = []
    stride = width * 4
    for y in range(height):
        line = buf[y * stride:(y + 1) * stride]
        rgb = bytearray(width * 3)
        rgb[0::3] = line[2::4]
        rgb[1::3] = line[1::4]
        rgb[2::3] = line[0::4]
        rows.append(bytes(rgb))
    return rows


# ------------------------------------------------------------------ Windows-Funktionen
if IS_WIN:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    gdi32 = ctypes.windll.gdi32

    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GetTickCount64.restype = ctypes.c_ulonglong
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.GetDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                    ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


def _key(vk: int, times: int = 1) -> None:
    for _ in range(times):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)   # KEYEVENTF_KEYUP


def screenshot_png(max_width: int = 1000) -> bytes:
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    w = min(max_width, sw)
    h = max(1, round(sh * w / sw))
    sdc = user32.GetDC(None)
    mdc = gdi32.CreateCompatibleDC(sdc)
    bmp = gdi32.CreateCompatibleBitmap(sdc, w, h)
    old = gdi32.SelectObject(mdc, bmp)
    try:
        gdi32.SetStretchBltMode(mdc, 4)  # HALFTONE: sauber verkleinert
        gdi32.StretchBlt(mdc, 0, 0, w, h, sdc, 0, 0, sw, sh, 0x00CC0020)
        bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
        return png_encode(w, h, bgra_to_rows(buf.raw, w, h))
    finally:
        gdi32.SelectObject(mdc, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(None, sdc)


def windows_name() -> str:
    if not IS_WIN:
        return platform.platform()
    ver = platform.version()          # z. B. 10.0.22631
    try:
        build = int(ver.split(".")[2])
    except (IndexError, ValueError):
        build = 0
    edition = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            edition = winreg.QueryValueEx(k, "EditionID")[0]
    except OSError:
        pass
    name = "Windows 11" if build >= 22000 else "Windows 10" if build >= 10240 else "Windows"
    return f"{name} {edition}".strip() + f" (Build {build})"


def main_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "–"


class WindowsBridge:
    """Alles, was die GlimraApp unter Windows auslösen kann."""
    platform = "windows"

    def __init__(self, notify_ui=None):
        self.notify_ui = notify_ui or (lambda text: None)

    # ---- Grundfunktionen (wie Glimra OS)
    def display_name(self) -> str:
        return getpass.getuser()

    def domain(self) -> str:
        dns = os.environ.get("USERDNSDOMAIN", "")
        nb = os.environ.get("USERDOMAIN", "")
        return dns.lower() if dns else ("" if nb.upper() == socket.gethostname().upper() else nb)

    def users(self) -> list[dict]:
        if not IS_WIN:
            return [{"user": getpass.getuser(), "session": "1", "state": "aktiv", "since": "", "current": True}]
        res = _run(["query", "user"])
        return parse_quser(res.stdout) or [{"user": getpass.getuser(), "session": "", "state": "aktiv",
                                            "since": "", "current": True}]

    def status(self) -> dict:
        ram = bat = up = "–"
        if IS_WIN:
            m = MEMORYSTATUSEX()
            m.dwLength = ctypes.sizeof(m)
            if kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                ram = f"{human(m.ullTotalPhys - m.ullAvailPhys)} / {human(m.ullTotalPhys)}"
            p = SYSTEM_POWER_STATUS()
            if kernel32.GetSystemPowerStatus(ctypes.byref(p)) and p.BatteryFlag != 128 and p.BatteryLifePercent != 255:
                bat = f"{p.BatteryLifePercent} %" + (" (lädt)" if p.ACLineStatus == 1 else "")
            up = duration(kernel32.GetTickCount64() / 1000)
        try:
            du = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\" if IS_WIN else "/")
            disk = f"{human(du.free)} frei von {human(du.total)}"
        except OSError:
            disk = "–"
        return {"hostname": socket.gethostname(), "user": self.display_name(), "os": windows_name(),
                "ram": ram, "uptime": up, "battery": bat, "ip": main_ip(), "disk": disk,
                "domain": self.domain(), "users": self.users(), "platform": "windows",
                "features": FEATURES, "launch": [{"id": k, "name": v[0]} for k, v in LAUNCH.items()]}

    def lock(self) -> None:
        if IS_WIN:
            user32.LockWorkStation()

    def clipboard_get(self) -> str:
        if not IS_WIN or not user32.OpenClipboard(None):
            return ""
        try:
            h = user32.GetClipboardData(13)  # CF_UNICODETEXT
            if not h:
                return ""
            p = kernel32.GlobalLock(h)
            try:
                return ctypes.wstring_at(p) if p else ""
            finally:
                kernel32.GlobalUnlock(h)
        finally:
            user32.CloseClipboard()

    def clipboard_set(self, text: str) -> None:
        if not IS_WIN:
            return
        data = (text + "\0").encode("utf-16-le")
        for _ in range(5):                     # Zwischenablage kann kurz belegt sein
            if user32.OpenClipboard(None):
                break
            time.sleep(0.1)
        else:
            return
        try:
            user32.EmptyClipboard()
            h = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
            p = kernel32.GlobalLock(h)
            ctypes.memmove(p, data, len(data))
            kernel32.GlobalUnlock(h)
            user32.SetClipboardData(13, h)
        finally:
            user32.CloseClipboard()

    def notify(self, text: str) -> None:
        self.notify_ui(text)
        self._message_box(text, "GlimraApp", wait=False)

    def open_url(self, url: str) -> None:
        webbrowser.open(url)

    def power(self, action: str) -> None:
        if not IS_WIN:
            return
        if action == "poweroff":
            _run(["shutdown", "/s", "/t", "5", "/c", "Ausschalten über die GlimraApp"])
        elif action == "reboot":
            _run(["shutdown", "/r", "/t", "5", "/c", "Neustart über die GlimraApp"])
        elif action == "suspend":
            ctypes.windll.powrprof.SetSuspendState(False, True, False)

    def volume(self, action: str) -> None:
        if IS_WIN:
            _key({"up": 0xAF, "down": 0xAE, "mute": 0xAD}[action], 1 if action == "mute" else 3)

    def media(self, action: str) -> None:
        if IS_WIN:
            _key({"play-pause": 0xB3, "next": 0xB0, "previous": 0xB1}[action])

    # ---- Zusatzfunktionen
    @staticmethod
    def _message_box(text: str, title: str, wait: bool) -> None:
        if not IS_WIN:
            return
        flags = 0x40 | 0x40000 | 0x10000  # Info-Symbol, immer im Vordergrund
        t = threading.Thread(target=lambda: user32.MessageBoxW(None, text, title, flags), daemon=True)
        t.start()
        if wait:
            t.join()

    def processes(self) -> list[dict]:
        if not IS_WIN:
            return []
        return parse_tasklist(_run(["tasklist", "/fo", "csv", "/nh"]).stdout)[:60]

    def handle_extra(self, method: str, path: str, data: dict):
        if method == "GET":
            if path == "/screen":
                if not IS_WIN:
                    return 404, {"error": "Nur unter Windows"}
                import base64
                return 200, {"png": base64.b64encode(screenshot_png()).decode("ascii")}
            if path == "/processes":
                return 200, {"processes": self.processes()}
            if path == "/users":
                return 200, {"domain": self.domain(), "users": self.users()}
            return None
        if path == "/kill":
            try:
                pid = int(data.get("pid", 0))
            except (TypeError, ValueError):
                return 400, {"error": "Ungültige Prozess-Nummer"}
            proc = next((p for p in self.processes() if p["pid"] == pid), None)
            if pid <= 4 or proc is None:
                return 404, {"error": "Programm läuft nicht mehr"}
            if proc["protected"]:
                return 403, {"error": f"{proc['name']} gehört zu Windows und wird nicht beendet"}
            res = _run(["taskkill", "/pid", str(pid), "/f"])
            return (200, {"ok": True}) if res.returncode == 0 else (400, {"error": "Beenden nicht erlaubt"})
        if path == "/message":
            text = str(data.get("text", ""))[:500]
            if not text:
                return 400, {"error": "Kein Text"}
            self._message_box(text, "Nachricht vom Handy", wait=False)
            return 200, {"ok": True}
        if path == "/logoff":
            if IS_WIN:
                _run(["shutdown", "/l"])
            return 200, {"ok": True}
        if path == "/hibernate":
            if IS_WIN:
                ctypes.windll.powrprof.SetSuspendState(True, True, False)
            return 200, {"ok": True}
        if path == "/launch":
            app = LAUNCH.get(str(data.get("app", "")))
            if not app:
                return 400, {"error": "Unbekanntes Programm"}
            if IS_WIN:
                subprocess.Popen(app[1], creationflags=NO_WINDOW)
            return 200, {"ok": True}
        return None


# ------------------------------------------------------------------ Starten / Autostart
def make_server(notify_ui=None) -> RemoteServer:
    return RemoteServer(WindowsBridge(notify_ui), CONFIG_DIR)


def agent_running(port: int = HTTP_PORT) -> bool:
    """Läuft der Agent schon (z. B. per Autostart im Hintergrund)?"""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/hello", timeout=1.5) as r:
            return b"glimra" in r.read()
    except OSError:
        return False


def local_call(path: str, body: dict | None = None, port: int = HTTP_PORT) -> dict:
    """Spricht mit dem Agenten auf diesem PC (nur von 127.0.0.1 erlaubt)."""
    import json
    import urllib.request
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 headers={"Content-Type": "application/json"}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.loads(r.read())


def autostart_enabled() -> bool:
    if not IS_WIN:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def set_autostart(on: bool) -> None:
    if not IS_WIN:
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            exe = sys.executable if getattr(sys, "frozen", False) else f'"{sys.executable}" -m glimra_setup'
            cmd = f'"{exe}" --agent' if getattr(sys, "frozen", False) else f"{exe} --agent"
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


def run_headless() -> None:
    """Nur der Agent: unsichtbar, bis Windows herunterfährt."""
    if agent_running():
        return
    srv = make_server()
    if not srv.start():
        return
    while True:
        time.sleep(3600)
