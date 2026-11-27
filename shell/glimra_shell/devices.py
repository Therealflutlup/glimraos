"""Schnelleinstellungen: WLAN, Bluetooth, Ton, Helligkeit, Flugmodus, Akku, Energieprofil.

Alles über kleine Kommandozeilenwerkzeuge (nmcli, bluetoothctl, wpctl/pactl, brightnessctl,
powerprofilesctl). Es läuft kein Dienst dauerhaft im Hintergrund – Werte werden nur abgefragt,
wenn die Schnelleinstellungen offen sind. Das hält RAM und CPU niedrig.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], timeout: int = 8) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def has(tool: str) -> bool:
    return shutil.which(tool) is not None


# ------------------------------------------------------------------ Ton
def volume() -> dict:
    """{'level': 0..100, 'muted': bool, 'available': bool}"""
    if not has("wpctl"):
        return {"level": 0, "muted": False, "available": False}
    out = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]).stdout
    m = re.search(r"Volume:\s*([\d.]+)", out)
    return {"level": round(float(m.group(1)) * 100) if m else 0, "muted": "MUTED" in out, "available": bool(m)}


def set_volume(level: int) -> None:
    level = max(0, min(150, int(level)))
    _run(["wpctl", "set-volume", "-l", "1.5", "@DEFAULT_AUDIO_SINK@", f"{level / 100:.2f}"])
    if level > 0:
        _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"])


def toggle_mute() -> None:
    _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])


def sinks() -> list[dict]:
    """Ausgabegeräte (Lautsprecher, Kopfhörer, HDMI …)."""
    if not has("pactl"):
        return []
    try:
        data = json.loads(_run(["pactl", "-f", "json", "list", "sinks"]).stdout or "[]")
        default = _run(["pactl", "get-default-sink"]).stdout.strip()
    except ValueError:
        return []
    return [{"name": s.get("name", ""), "label": s.get("description", s.get("name", "")),
             "default": s.get("name") == default} for s in data]


def set_sink(name: str) -> None:
    if re.fullmatch(r"[\w.:-]+", name):
        _run(["pactl", "set-default-sink", name])


# ------------------------------------------------------------------ Helligkeit
def brightness() -> dict:
    if not has("brightnessctl"):
        return {"level": 0, "available": False}
    cur = _run(["brightnessctl", "-m", "info"]).stdout  # name,class,current,percent%,max
    parts = cur.strip().split(",")
    if len(parts) >= 4 and parts[1] == "backlight":
        return {"level": int(parts[3].rstrip("%") or 0), "available": True}
    return {"level": 0, "available": False}


def set_brightness(level: int) -> None:
    _run(["brightnessctl", "-q", "set", f"{max(5, min(100, int(level)))}%"])


# ------------------------------------------------------------------ WLAN
def wifi_state() -> dict:
    if not has("nmcli"):
        return {"available": False, "enabled": False, "connected": ""}
    enabled = _run(["nmcli", "radio", "wifi"]).stdout.strip() == "enabled"
    conn = ""
    for line in _run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"]).stdout.splitlines():
        if line.startswith("yes:"):
            conn = line[4:].replace("\\:", ":")
            break
    return {"available": True, "enabled": enabled, "connected": conn}


def wifi_list() -> list[dict]:
    if not has("nmcli"):
        return []
    out = _run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "auto"], 15).stdout
    nets, seen = [], set()
    for line in out.splitlines():
        parts = re.split(r"(?<!\\):", line)
        if len(parts) < 4 or not parts[1] or parts[1] in seen:
            continue
        seen.add(parts[1])
        nets.append({"ssid": parts[1].replace("\\:", ":"), "signal": int(parts[2] or 0),
                     "secure": parts[3] not in ("", "--"), "active": parts[0] == "*"})
    return sorted(nets, key=lambda n: (not n["active"], -n["signal"]))[:20]


def set_wifi(on: bool) -> None:
    _run(["nmcli", "radio", "wifi", "on" if on else "off"])


def wifi_connect(ssid: str, password: str) -> tuple[bool, str]:
    cmd = ["nmcli", "dev", "wifi", "connect", ssid]
    if password:
        cmd += ["password", password]
    res = _run(cmd, 45)
    if res.returncode == 0:
        return True, f"Verbunden mit {ssid}."
    if "Secrets were required" in res.stderr or "password" in res.stderr.lower():
        return False, "Falsches WLAN-Passwort."
    return False, f"Verbindung mit {ssid} fehlgeschlagen."


# ------------------------------------------------------------------ Bluetooth
def bt_state() -> dict:
    if not has("bluetoothctl"):
        return {"available": False, "enabled": False}
    out = _run(["bluetoothctl", "show"]).stdout
    if "No default controller" in out or not out:
        return {"available": False, "enabled": False}
    return {"available": True, "enabled": "Powered: yes" in out}


def set_bt(on: bool) -> None:
    _run(["bluetoothctl", "power", "on" if on else "off"])


def bt_devices(scan: bool = False) -> list[dict]:
    if not has("bluetoothctl"):
        return []
    if scan:
        _run(["bluetoothctl", "--timeout", "8", "scan", "on"], 12)
    devs = []
    paired = {m for m in re.findall(r"Device (\S+)", _run(["bluetoothctl", "devices", "Paired"]).stdout)}
    for mac, name in re.findall(r"Device (\S+) (.+)", _run(["bluetoothctl", "devices"]).stdout):
        info = _run(["bluetoothctl", "info", mac]).stdout
        devs.append({"mac": mac, "name": name.strip(), "paired": mac in paired, "connected": "Connected: yes" in info})
    return sorted(devs, key=lambda d: (not d["connected"], not d["paired"], d["name"]))[:20]


def bt_connect(mac: str) -> tuple[bool, str]:
    if not re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac, re.I):
        return False, "Ungültiges Gerät."
    for step in (["pair", mac], ["trust", mac]):
        _run(["bluetoothctl", "--timeout", "15", *step], 20)
    res = _run(["bluetoothctl", "--timeout", "15", "connect", mac], 20)
    return ("Connection successful" in res.stdout, "Verbunden." if "Connection successful" in res.stdout
            else "Verbinden fehlgeschlagen – ist das Gerät im Kopplungsmodus?")


def bt_disconnect(mac: str) -> None:
    if re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", mac, re.I):
        _run(["bluetoothctl", "disconnect", mac])


# ------------------------------------------------------------------ Flugmodus, Akku, Energie
def airplane() -> bool:
    if not has("nmcli"):
        return False
    return _run(["nmcli", "radio", "all"]).stdout.split()[-2:] == ["disabled", "disabled"]


def set_airplane(on: bool) -> None:
    _run(["nmcli", "radio", "all", "off" if on else "on"])
    if has("bluetoothctl"):
        set_bt(not on)


def battery() -> dict:
    for b in sorted(Path("/sys/class/power_supply").glob("BAT*")):
        try:
            cap = int((b / "capacity").read_text().strip())
            status = (b / "status").read_text().strip()
        except (OSError, ValueError):
            continue
        return {"present": True, "level": cap, "charging": status in ("Charging", "Full")}
    return {"present": False, "level": 100, "charging": False}


PROFILES = {"power-saver": "Energiesparen", "balanced": "Ausgeglichen", "performance": "Leistung"}


def power_profile() -> dict:
    if not has("powerprofilesctl"):
        return {"available": False, "current": "", "options": []}
    cur = _run(["powerprofilesctl", "get"]).stdout.strip()
    opts = [p for p in PROFILES if p in _run(["powerprofilesctl", "list"]).stdout]
    return {"available": True, "current": cur, "options": [{"id": p, "label": PROFILES[p]} for p in opts]}


def set_power_profile(profile: str) -> None:
    if profile in PROFILES:
        _run(["powerprofilesctl", "set", profile])
