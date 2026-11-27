"""Glimra Shell – Python-Backend.

Stellt der QML-Oberfläche Systemfunktionen bereit: Programme starten,
Einstellungen speichern, Netzwerk-Infos, Prozessliste, Profile installieren.
Läuft unter Glimra OS (Linux) und im Vorschau-Modus auch unter Windows.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import hashlib
import secrets
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from . import CODENAME, __version__, devices, installer, store, sysops
from .assistant import Assistant
from .remote import RemoteServer, HTTP_PORT

IS_LINUX = sys.platform.startswith("linux")

CONFIG_DIR = Path.home() / ".config" / "glimra"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
DESKTOP_DIR = Path.home() / "Desktop"

DEFAULT_SETTINGS = {
    "setupDone": False,
    "name": "",
    "email": "",
    "profile": "",          # gaming | leistung | arbeit | apps
    "wallpaper": "aurora",  # aurora | sunset | ocean | forest | night | auto
    "accent": "#5b8cff",
    "remote": True,         # Handy-Fernsteuerung (GlimraApp) erlaubt
    "pinHash": "",
    "pinSalt": "",
}
SETTINGS_EXPORT_KEYS = ("name", "email", "profile", "wallpaper", "accent")

# Die Paketlisten der Nutzungsprofile stehen in /usr/local/bin/glimra-profile.
PROFILES = ("gaming", "leistung", "arbeit", "apps", "vm", "assistent")
PROFILE_TOOL = "/usr/local/bin/glimra-profile"


class Backend(QObject):
    settingsChanged = Signal()
    message = Signal(str)          # kurze Meldung für die Oberfläche (Toast)
    desktopChanged = Signal()
    lockRequested = Signal()
    remoteChanged = Signal()
    taskDone = Signal(str, bool, str)        # Art, erfolgreich, Text
    taskProgress = Signal(str, str)          # Art, Text
    assistantReply = Signal(str, str, str, str)  # gehört, Antwort, Aktion, Wert
    quickStateReady = Signal("QVariantMap")
    listReady = Signal(str, "QVariantList")      # Art (wifi, bt, store, featured, updates, sinks), Einträge
    clipHistoryChanged = Signal()
    updatesAvailable = Signal(int)
    shortcut = Signal(str)
    indexReady = Signal()
    _clipboardSet = Signal(str)

    def __init__(self, glimra_mode: bool, wayland_socket: str = "wayland-glimra"):
        super().__init__()
        self._glimra = glimra_mode
        self._socket = wayland_socket
        self._settings = dict(DEFAULT_SETTINGS)
        self._load()
        self._clip_cache = ""
        self._clip_history: list[str] = []
        self._window = None
        self._file_index: list[tuple[str, str]] = []
        self._index_time = 0.0
        self._index_busy = False
        self._clipboardSet.connect(self._apply_clipboard)
        cb = QGuiApplication.clipboard()
        cb.dataChanged.connect(self._clip_changed)
        self._assistant = Assistant(lambda: {"ip": self._main_ip()})
        self._remote = RemoteServer(self, CONFIG_DIR)
        self._remote.on_change = self.remoteChanged.emit
        self._remote.on_transfer = lambda path: self.taskProgress.emit("transfer", Path(path).name)
        if self._glimra and IS_LINUX:
            if self._settings.get("remote", True):
                self._remote.start()
            threading.Thread(target=self._boot_ok, daemon=True).start()
            # Updates alle 6 Stunden im Hintergrund prüfen (erste Prüfung nach 10 Minuten)
            self._update_timer = QTimer(self)
            self._update_timer.setInterval(6 * 3600 * 1000)
            self._update_timer.timeout.connect(self.checkUpdatesQuiet)
            self._update_timer.start()
            QTimer.singleShot(10 * 60 * 1000, self.checkUpdatesQuiet)

    @staticmethod
    def _boot_ok() -> None:
        # meldet dem Boot-Check: System ist erfolgreich gestartet
        if Path("/usr/local/bin/glimra-bootok").exists():
            sysops.run(sysops._root_cmd(["/usr/local/bin/glimra-bootok"]), timeout=10)

    def _async(self, kind: str, fn, *args) -> None:
        def worker():
            try:
                ok, text = fn(*args)
            except Exception as e:  # noqa: BLE001 – Fehler als Meldung anzeigen
                ok, text = False, f"Fehler: {e}"
            self.taskDone.emit(kind, ok, text)
        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------ Einstellungen
    def _load(self) -> None:
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            self._settings.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
        except (OSError, ValueError):
            pass

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(self._settings, indent=2, ensure_ascii=False), encoding="utf-8")

    def _get_settings(self):
        return dict(self._settings)

    settings = Property("QVariantMap", _get_settings, notify=settingsChanged)

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value) -> None:
        if key not in DEFAULT_SETTINGS:
            return
        self._settings[key] = value
        self._save()
        self.settingsChanged.emit()

    @Slot()
    def resetSetup(self) -> None:
        self._settings["setupDone"] = False
        self._save()
        self.settingsChanged.emit()

    # ------------------------------------------------------------ Systeminfos
    def _is_glimra(self):
        return self._glimra

    isGlimra = Property(bool, _is_glimra, constant=True)

    def _version(self) -> str:
        try:
            return Path("/etc/glimra/version").read_text().strip() or __version__
        except OSError:
            return __version__

    version = Property(str, _version, constant=True)
    codename = Property(str, lambda self: CODENAME, constant=True)

    # ------------------------------------------------------------ Installer (Live-System)
    isLive = Property(bool, lambda self: installer.is_live(), constant=True)
    edition = Property(str, lambda self: installer.edition(), constant=True)

    @Slot(result="QVariantList")
    def installerDisks(self):
        return installer.list_disks()

    @Slot(str, str, str, str, str, result=str)
    def installerCheck(self, host: str, user: str, pw1: str, pw2: str, panel_pw: str) -> str:
        return installer.validate(host, user, pw1, pw2, panel_pw, installer.edition())

    @Slot()
    def checkInternet(self) -> None:
        self._async("net", lambda: (installer.has_internet(), ""))

    @Slot(str, str, str, str, str)
    def startInstall(self, disk: str, host: str, user: str, password: str, panel_pw: str) -> None:
        err = installer.validate(host, user, password, password, panel_pw, installer.edition())
        if err:
            self.taskDone.emit("install", False, err)
            return
        log = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "glimra-install.log"

        def work():
            return installer.run_install(
                disk, host, user, password, panel_pw,
                on_step=lambda n, total, text: self.taskProgress.emit("install-step", f"{n}|{total}|{text}"),
                on_log=lambda line: self.taskProgress.emit("install-log", line),
                log_file=log)
        self._async("install", work)

    @Slot(result=str)
    def hostname(self) -> str:
        return socket.gethostname()

    @Slot(result="QVariantMap")
    def systemInfo(self):
        info = {
            "os": "Glimra OS" if self._glimra else f"Vorschau auf {platform.system()} {platform.release()}",
            "kernel": platform.release(),
            "hostname": socket.gethostname(),
            "cpu": platform.processor() or platform.machine(),
            "ramTotal": "",
            "ramUsed": "",
            "uptime": "",
        }
        if IS_LINUX:
            try:
                mem = {}
                for line in Path("/proc/meminfo").read_text().splitlines():
                    k, v = line.split(":", 1)
                    mem[k] = int(v.split()[0])
                total = mem["MemTotal"] / 1024 / 1024
                used = (mem["MemTotal"] - mem.get("MemAvailable", 0)) / 1024 / 1024
                info["ramTotal"] = f"{total:.1f} GB"
                info["ramUsed"] = f"{used:.1f} GB"
                secs = float(Path("/proc/uptime").read_text().split()[0])
                info["uptime"] = f"{int(secs // 3600)} h {int(secs % 3600 // 60)} min"
                for line in Path("/proc/cpuinfo").read_text().splitlines():
                    if line.startswith("model name"):
                        info["cpu"] = line.split(":", 1)[1].strip()
                        break
            except (OSError, ValueError, KeyError):
                pass
        return info

    @Slot(result="QVariantList")
    def networkInfo(self):
        """Netzwerkkarten mit IP- und MAC-Adresse."""
        result = []
        if IS_LINUX and shutil.which("ip"):
            try:
                out = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True, timeout=3).stdout
                for iface in json.loads(out or "[]"):
                    name = iface.get("ifname", "?")
                    if name == "lo":
                        continue
                    ipv4 = [a["local"] for a in iface.get("addr_info", []) if a.get("family") == "inet"]
                    ipv6 = [a["local"] for a in iface.get("addr_info", []) if a.get("family") == "inet6"]
                    result.append({
                        "name": name,
                        "mac": iface.get("address", "–"),
                        "ipv4": ", ".join(ipv4) or "–",
                        "ipv6": ", ".join(ipv6) or "–",
                        "state": iface.get("operstate", "?"),
                    })
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        if not result:
            # Fallback (z. B. Windows-Vorschau)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("10.255.255.255", 1))
                ip = s.getsockname()[0]
                s.close()
            except OSError:
                ip = "–"
            import uuid
            mac = ":".join(f"{(uuid.getnode() >> i) & 0xff:02x}" for i in range(40, -1, -8))
            result.append({"name": "Standard", "mac": mac, "ipv4": ip, "ipv6": "–", "state": "UP"})
        return result

    @Slot(result="QVariantMap")
    def routeInfo(self):
        gateway, dns = "–", []
        if IS_LINUX:
            try:
                out = subprocess.run(["ip", "-j", "route", "show", "default"], capture_output=True,
                                     text=True, timeout=3).stdout
                routes = json.loads(out or "[]")
                if routes:
                    gateway = routes[0].get("gateway", "–")
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            try:
                for line in Path("/etc/resolv.conf").read_text().splitlines():
                    if line.startswith("nameserver"):
                        dns.append(line.split()[1])
            except OSError:
                pass
        return {"gateway": gateway, "dns": ", ".join(dns) or "–"}

    @Slot(result="QVariantList")
    def processes(self):
        """Prozessliste für den Taskmanager (Name, PID, RAM in MB)."""
        procs = []
        if IS_LINUX:
            for d in Path("/proc").iterdir():
                if not d.name.isdigit():
                    continue
                try:
                    name = (d / "comm").read_text().strip()
                    rss = 0
                    for line in (d / "status").read_text().splitlines():
                        if line.startswith("VmRSS:"):
                            rss = int(line.split()[1]) // 1024
                            break
                    procs.append({"pid": int(d.name), "name": name, "mem": rss})
                except (OSError, ValueError):
                    continue
        else:
            procs.append({"pid": os.getpid(), "name": "glimra-shell (Vorschau)", "mem": 0})
        procs.sort(key=lambda p: p["mem"], reverse=True)
        return procs[:80]

    @Slot(int)
    def killProcess(self, pid: int) -> None:
        if pid == os.getpid():
            self.message.emit("Die Glimra Shell kann sich nicht selbst beenden.")
            return
        try:
            os.kill(pid, 15)
            self.message.emit(f"Prozess {pid} beendet.")
        except OSError as e:
            self.message.emit(f"Konnte Prozess {pid} nicht beenden: {e.strerror}")

    # ------------------------------------------------------------ Programme
    def _client_env(self):
        env = dict(os.environ)
        env.update({
            "WAYLAND_DISPLAY": self._socket,
            "QT_QPA_PLATFORM": "wayland",
            "GDK_BACKEND": "wayland",
            "MOZ_ENABLE_WAYLAND": "1",
            "SDL_VIDEODRIVER": "wayland",
            "XDG_SESSION_TYPE": "wayland",
            "XDG_CURRENT_DESKTOP": "Glimra",
        })
        env.pop("QT_QPA_EGLFS_INTEGRATION", None)
        return env

    @Slot(str, result=bool)
    def launch(self, command: str) -> bool:
        """Startet ein Programm als Fenster in der Glimra Shell."""
        if not self._glimra:
            self.message.emit("Programme starten geht nur unter Glimra OS – das hier ist die Vorschau.")
            return False
        args = command.split()
        if not args or not shutil.which(args[0]):
            self.message.emit(f"„{args[0] if args else command}“ ist nicht installiert.")
            return False
        subprocess.Popen(args, env=self._client_env(), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    @Slot(str)
    def openPath(self, path: str) -> None:
        """Öffnet eine Datei passend zur Endung: .sh, .exe/.bat (Wine), Ordner …"""
        p = Path(path)
        ext = p.suffix.lower()
        if p.is_dir():
            self.launch(f"pcmanfm-qt {p}")
        elif ext == ".sh":
            self.launch(f"foot --hold bash {p}")
        elif ext in (".exe", ".bat", ".msi"):
            if shutil.which("wine"):
                self.launch(f"glimra-x11 wine {p}")
            else:
                self.message.emit("Für .exe/.bat wird Wine gebraucht – wähle in den Einstellungen das Gaming-Profil.")
        else:
            self.launch(f"xdg-open {p}")

    # ------------------------------------------------------------ Desktop
    @Slot(result="QVariantList")
    def desktopEntries(self):
        DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
        items = []
        for e in sorted(DESKTOP_DIR.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if e.name.startswith("."):
                continue
            items.append({"name": e.name, "path": str(e), "dir": e.is_dir(), "ext": e.suffix.lower()})
        return items

    @Slot()
    def newFolder(self) -> None:
        DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
        base, n = "Neuer Ordner", 1
        target = DESKTOP_DIR / base
        while target.exists():
            n += 1
            target = DESKTOP_DIR / f"{base} ({n})"
        target.mkdir()
        self.desktopChanged.emit()

    # ------------------------------------------------------------ Profile & System
    @Slot(str)
    def applyProfile(self, profile: str) -> None:
        """Installiert die Pakete für das gewählte Nutzungsprofil im Hintergrund."""
        if profile not in PROFILES:
            return
        if not (self._glimra and Path(PROFILE_TOOL).exists()):
            self.message.emit(f"Profil „{profile}“ gespeichert (Installation nur unter Glimra OS).")
            return

        def run():
            self.message.emit("Wird installiert … das kann ein paar Minuten dauern.")
            cmd = [PROFILE_TOOL, profile]
            if os.geteuid() != 0:
                # ohne Passwort erlaubt über /etc/sudoers.d/20-glimra (nur dieses Werkzeug)
                cmd = ["sudo", "-n", *cmd]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                self.message.emit("Installiert. Viel Spaß!")
                self.taskDone.emit("profile", True, profile)
            else:
                self.message.emit("Installation fehlgeschlagen – bist du mit dem Internet verbunden?")
                self.taskDone.emit("profile", False, profile)

        threading.Thread(target=run, daemon=True).start()

    @Slot(str)
    def power(self, action: str) -> None:
        if not self._glimra:
            self.message.emit("Ausschalten/Neustarten geht nur unter Glimra OS.")
            return
        if action in ("poweroff", "reboot", "suspend"):
            subprocess.Popen(["systemctl", action])

    # ------------------------------------------------------------ Hilfsfunktionen
    def _main_ip(self) -> str:
        # Die Adresse, über die der PC ins Netz geht (nicht virbr0/docker0 o. Ä.)
        if IS_LINUX and shutil.which("ip"):
            try:
                out = subprocess.run(["ip", "-4", "route", "get", "1.1.1.1"], capture_output=True,
                                     text=True, timeout=3).stdout.split()
                if "src" in out:
                    return out[out.index("src") + 1]
            except (OSError, subprocess.SubprocessError, IndexError):
                pass
        for n in self.networkInfo():
            if n["ipv4"] != "–":
                return n["ipv4"].split(",")[0]
        return "–"

    def display_name(self) -> str:
        return self._settings.get("name") or "Glimra"

    # Brücke für den Remote-Server (läuft in eigenem Thread)
    def status(self) -> dict:
        info = self.systemInfo()
        bat = ""
        for b in Path("/sys/class/power_supply").glob("BAT*"):
            try:
                bat = (b / "capacity").read_text().strip() + " %"
            except OSError:
                pass
        return {"hostname": info["hostname"], "user": self.display_name(), "os": info["os"],
                "ram": f'{info["ramUsed"]} / {info["ramTotal"]}' if info["ramUsed"] else "–",
                "uptime": info["uptime"] or "–", "battery": bat or "–", "ip": self._main_ip()}

    def lock(self) -> None:
        self.lockRequested.emit()

    def clipboard_get(self) -> str:
        return self._clip_cache

    def clipboard_set(self, text: str) -> None:
        self._clipboardSet.emit(text)

    def notify(self, text: str) -> None:
        self.message.emit(text)

    def open_url(self, url: str) -> None:
        self.launch(f"firefox {url}")

    def volume(self, action: str) -> None:
        if shutil.which("wpctl"):
            arg = {"up": ["set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "5%+"],
                   "down": ["set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"],
                   "mute": ["set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"]}[action]
            subprocess.run(["wpctl", *arg], capture_output=True)

    def media(self, action: str) -> None:
        if shutil.which("playerctl"):
            subprocess.run(["playerctl", action], capture_output=True)

    def _clip_changed(self) -> None:
        text = QGuiApplication.clipboard().text()
        self._clip_cache = text
        if text.strip():
            self._clip_history = [text] + [t for t in self._clip_history if t != text]
            del self._clip_history[25:]
            self.clipHistoryChanged.emit()

    def _apply_clipboard(self, text: str) -> None:
        QGuiApplication.clipboard().setText(text)
        self._clip_cache = text
        self.message.emit("Zwischenablage vom Handy übernommen.")

    @Slot(str)
    def toast(self, text: str) -> None:
        self.message.emit(text)

    # ------------------------------------------------------------ Handy / Remote (QML)
    @Slot(result="QVariantMap")
    def remoteInfo(self):
        return {"enabled": self._remote.running, "ip": self._main_ip(), "port": HTTP_PORT,
                "code": self._remote.pair_code, "transferCode": self._remote.transfer_code,
                "devices": [{"name": d["name"], "since": d.get("since", "")} for d in self._remote.devices()]}

    @Slot(bool)
    def setRemoteEnabled(self, on: bool) -> None:
        self.setSetting("remote", on)
        if on and self._glimra:
            if not self._remote.start():
                self.message.emit("Port 8765 ist belegt – Fernsteuerung konnte nicht starten.")
        else:
            self._remote.stop()
        self.remoteChanged.emit()

    @Slot()
    def newPairCode(self) -> None:
        self._remote.new_pair_code()

    @Slot()
    def newTransferCode(self) -> None:
        self._remote.new_transfer_code()

    @Slot(str)
    def removeDevice(self, name: str) -> None:
        self._remote.remove_device(name)

    # ------------------------------------------------------------ Sperrbildschirm / Konto
    @Slot(result=bool)
    def hasPin(self) -> bool:
        return bool(self._settings.get("pinHash"))

    @Slot(str, result=bool)
    def setPin(self, pin: str) -> bool:
        if pin and not (pin.isdigit() and 4 <= len(pin) <= 8):
            return False
        if not pin:
            self._settings.update(pinHash="", pinSalt="")
        else:
            salt = secrets.token_hex(8)
            self._settings.update(pinSalt=salt, pinHash=hashlib.sha256((salt + pin).encode()).hexdigest())
        self._save()
        self.settingsChanged.emit()
        return True

    @Slot(str, result=bool)
    def checkPin(self, pin: str) -> bool:
        if not self.hasPin():
            return True
        h = hashlib.sha256((self._settings["pinSalt"] + pin).encode()).hexdigest()
        if secrets.compare_digest(h, self._settings["pinHash"]):
            return True
        time.sleep(0.6)
        return False

    @Slot()
    def lockNow(self) -> None:
        self.lockRequested.emit()

    @Slot(result=str)
    def exportSettings(self) -> str:
        target = Path.home() / "glimra-konto.json"
        data = {k: self._settings.get(k) for k in SETTINGS_EXPORT_KEYS}
        target.write_text(json.dumps({"glimraKonto": 1, **data}, indent=2, ensure_ascii=False), encoding="utf-8")
        self.message.emit(f"Konto gespeichert: {target}")
        return str(target)

    @Slot(result=bool)
    def importSettings(self) -> bool:
        src = Path.home() / "glimra-konto.json"
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.message.emit("Keine glimra-konto.json im persönlichen Ordner gefunden.")
            return False
        for k in SETTINGS_EXPORT_KEYS:
            if k in data:
                self._settings[k] = data[k]
        self._save()
        self.settingsChanged.emit()
        self.message.emit("Konto übernommen.")
        return True

    # ------------------------------------------------------------ Assistent
    @Slot(result=bool)
    def voiceAvailable(self) -> bool:
        return self._assistant.voice_available()

    @Slot(str)
    def ask(self, text: str) -> None:
        reply, action, value = self._assistant.ask(text)
        self._assistant_action(action, value)
        self.assistantReply.emit(text, reply, action, value)
        self._assistant.speak(reply)

    @Slot()
    def listen(self) -> None:
        def worker():
            try:
                heard = self._assistant.listen()
            except Exception as e:  # noqa: BLE001
                self.assistantReply.emit("", f"Mikrofon-Fehler: {e}", "", "")
                return
            if not heard:
                self.assistantReply.emit("", "Ich habe nichts gehört.", "", "")
                return
            reply, action, value = self._assistant.ask(heard)
            self._assistant_action(action, value)
            self.assistantReply.emit(heard, reply, action, value)
            self._assistant.speak(reply)
        threading.Thread(target=worker, daemon=True).start()

    def _assistant_action(self, action: str, value: str) -> None:
        if action == "volume":
            self.volume(value)
        elif action == "wallpaper":
            self.setSetting("wallpaper", value)
        elif action == "search":
            import urllib.parse
            self.launch("firefox https://duckduckgo.com/?q=" + urllib.parse.quote(value))
        elif action == "lock":
            self.lockRequested.emit()

    # ------------------------------------------------------------ Sicherheit
    @Slot(result="QVariantMap")
    def securityStatus(self):
        if not IS_LINUX:
            return {"firewall": "Vorschau", "db": "", "clamav": False}
        return sysops.security_status()

    @Slot(bool)
    def setFirewall(self, on: bool) -> None:
        self._async("firewall", sysops.set_firewall, on)

    @Slot()
    def updateVirusDb(self) -> None:
        self._async("virusdb", sysops.update_virus_db)

    @Slot(str)
    def virusScan(self, path: str) -> None:
        self._async("scan", sysops.virus_scan, path or str(Path.home()))

    # ------------------------------------------------------------ Backups
    @Slot(result="QVariantList")
    def snapshots(self):
        return sysops.snapshots() if IS_LINUX else []

    @Slot(str)
    def createSnapshot(self, desc: str) -> None:
        self._async("snapshot", sysops.create_snapshot, desc)

    @Slot(int)
    def restoreSnapshot(self, number: int) -> None:
        self._async("restore", sysops.restore_snapshot, number)

    # ------------------------------------------------------------ Virtuelle PCs
    @Slot(result=bool)
    def vmAvailable(self) -> bool:
        return IS_LINUX and sysops.vm_available()

    @Slot(result="QVariantList")
    def vmList(self):
        return sysops.vm_list() if IS_LINUX else []

    @Slot(result="QVariantList")
    def isoFiles(self):
        return sysops.iso_files()

    @Slot(str, str, int, int)
    def vmCreate(self, name: str, iso: str, ram: int, disk: int) -> None:
        self._async("vm", sysops.vm_create, name, iso, ram, disk)

    @Slot(str, str)
    def vmAction(self, name: str, action: str) -> None:
        self._async("vm", sysops.vm_action, name, action, self.launch)

    # ------------------------------------------------------------ Umzug
    @Slot(result="QVariantList")
    def transferSources(self):
        return sysops.transfer_sources()

    @Slot(str, "QVariantList")
    def importFrom(self, source: str, categories) -> None:
        cats = [str(c) for c in categories]
        self._async("import", sysops.import_from, source, cats,
                    lambda t: self.taskProgress.emit("import", t))

    @Slot(result="QVariantList")
    def wallpaperImages(self):
        return sysops.wallpaper_images()

    # ------------------------------------------------------------ Hilfe
    @Slot(result=str)
    def systemReport(self) -> str:
        log = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "glimra-shell.log"
        path = sysops.system_report(log)
        self.message.emit("Systembericht liegt auf dem Desktop.")
        self.desktopChanged.emit()
        return path

    @Slot(result="QVariantList")
    def shortcutHelp(self):
        from .keys import HELP
        return [{"keys": k, "action": a} for k, a in HELP]

    # ------------------------------------------------------------ Zwischenablage-Verlauf (Win+V)
    def _get_clip_history(self):
        return list(self._clip_history)

    clipHistory = Property("QVariantList", _get_clip_history, notify=clipHistoryChanged)

    @Slot(int)
    def clipboardPick(self, index: int) -> None:
        if 0 <= index < len(self._clip_history):
            QGuiApplication.clipboard().setText(self._clip_history[index])

    @Slot()
    def clipboardClear(self) -> None:
        self._clip_history.clear()
        self.clipHistoryChanged.emit()

    # ------------------------------------------------------------ Bildschirmfoto (Druck, Win+Umschalt+S)
    def set_window(self, window) -> None:
        self._window = window

    @Slot()
    def screenshot(self) -> None:
        QTimer.singleShot(250, self._take_screenshot)  # Menüs erst schließen lassen

    def _take_screenshot(self) -> None:
        if self._window is None:
            return
        img = self._window.grabWindow()
        folder = Path.home() / "Bilder" / "Bildschirmfotos"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / time.strftime("Bildschirmfoto_%Y-%m-%d_%H-%M-%S.png")
        img.save(str(target))
        QGuiApplication.clipboard().setImage(img)
        self.message.emit("Bildschirmfoto gespeichert und kopiert.")

    # ------------------------------------------------------------ Schnelleinstellungen
    def _bg(self, fn, *args) -> None:
        threading.Thread(target=fn, args=args, daemon=True).start()

    @Slot()
    def requestQuickState(self) -> None:
        def work():
            if not IS_LINUX:
                state = {"volume": {"level": 60, "muted": False, "available": False},
                         "brightness": {"level": 80, "available": False},
                         "wifi": {"available": False, "enabled": False, "connected": ""},
                         "bt": {"available": False, "enabled": False}, "airplane": False,
                         "battery": {"present": False, "level": 100, "charging": False},
                         "power": {"available": False, "current": "", "options": []}}
            else:
                state = {"volume": devices.volume(), "brightness": devices.brightness(), "wifi": devices.wifi_state(),
                         "bt": devices.bt_state(), "airplane": devices.airplane(), "battery": devices.battery(),
                         "power": devices.power_profile()}
            self.quickStateReady.emit(state)
        self._bg(work)

    @Slot(result="QVariantMap")
    def batteryInfo(self):
        return devices.battery()

    @Slot(int)
    def setVolume(self, level: int) -> None:
        self._bg(devices.set_volume, level)

    @Slot()
    def toggleMute(self) -> None:
        self._bg(devices.toggle_mute)

    @Slot(int)
    def setBrightness(self, level: int) -> None:
        self._bg(devices.set_brightness, level)

    @Slot(bool)
    def setWifi(self, on: bool) -> None:
        self._bg(lambda: (devices.set_wifi(on), self.requestQuickState()))

    @Slot(bool)
    def setBluetooth(self, on: bool) -> None:
        self._bg(lambda: (devices.set_bt(on), self.requestQuickState()))

    @Slot(bool)
    def setAirplane(self, on: bool) -> None:
        self._bg(lambda: (devices.set_airplane(on), self.requestQuickState()))

    @Slot(str)
    def setPowerProfile(self, profile: str) -> None:
        self._bg(lambda: (devices.set_power_profile(profile), self.requestQuickState()))

    @Slot()
    def requestWifiList(self) -> None:
        self._bg(lambda: self.listReady.emit("wifi", devices.wifi_list() if IS_LINUX else []))

    @Slot(str, str)
    def wifiConnect(self, ssid: str, password: str) -> None:
        self._async("wifi", devices.wifi_connect, ssid, password)

    @Slot(bool)
    def requestBtDevices(self, scan: bool) -> None:
        self._bg(lambda: self.listReady.emit("bt", devices.bt_devices(scan) if IS_LINUX else []))

    @Slot(str)
    def btConnect(self, mac: str) -> None:
        self._async("bt", devices.bt_connect, mac)

    @Slot(str)
    def btDisconnect(self, mac: str) -> None:
        self._bg(devices.bt_disconnect, mac)

    @Slot()
    def requestSinks(self) -> None:
        self._bg(lambda: self.listReady.emit("sinks", devices.sinks() if IS_LINUX else []))

    @Slot(str)
    def setSink(self, name: str) -> None:
        self._bg(devices.set_sink, name)

    # ------------------------------------------------------------ Glimra Store & Update
    @Slot()
    def requestFeatured(self) -> None:
        self._bg(lambda: self.listReady.emit("featured", store.featured()))

    @Slot(str)
    def storeSearch(self, query: str) -> None:
        self._bg(lambda: self.listReady.emit("store", store.search(query)))

    @Slot(str)
    def storeInstall(self, pkg: str) -> None:
        if not self._lumen:
            self.message.emit("Installieren geht nur unter Glimra OS – das hier ist die Vorschau.")
            return
        self.message.emit("Wird installiert …")
        self._async("install", store.install, pkg)

    @Slot(str)
    def storeRemove(self, pkg: str) -> None:
        if not self._lumen:
            self.message.emit("Entfernen geht nur unter Glimra OS – das hier ist die Vorschau.")
            return
        self._async("remove", store.remove, pkg)

    @Slot()
    def requestUpdates(self) -> None:
        def work():
            ups = store.check_updates() if IS_LINUX else []
            self.listReady.emit("updates", ups)
        self._bg(work)

    @Slot()
    def checkUpdatesQuiet(self) -> None:
        def work():
            n = len(store.check_updates())
            if n:
                self.updatesAvailable.emit(n)
                self.message.emit(f"{n} Updates verfügbar – Glimra Update öffnen.")
        self._bg(work)

    @Slot()
    def runUpdates(self) -> None:
        if not self._lumen:
            self.message.emit("Updates gehen nur unter Glimra OS – das hier ist die Vorschau.")
            return
        self._async("update", store.run_updates, lambda t: self.taskProgress.emit("update", t))

    # ------------------------------------------------------------ Suche (Startmenü)
    def _build_index(self) -> None:
        entries: list[tuple[str, str]] = []
        home = Path.home()
        skip = {"node_modules", "__pycache__", "venv", ".venv", "snap", "go"}
        for root, dirs, files in os.walk(home):
            depth = len(Path(root).relative_to(home).parts)
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip and depth < 5]
            for name in files + dirs:
                if not name.startswith("."):
                    entries.append((name.lower(), os.path.join(root, name)))
            if len(entries) > 20000:
                break
        self._file_index = entries
        self._index_time = time.time()
        self._index_busy = False
        self.indexReady.emit()

    @Slot(str, result="QVariantList")
    def searchFiles(self, query: str):
        q = query.strip().lower()
        if time.time() - self._index_time > 600 and not self._index_busy:
            self._index_busy = True
            self._bg(self._build_index)
        if len(q) < 2:
            return []
        hits = [p for n, p in self._file_index if q in n]
        hits.sort(key=lambda p: (not Path(p).name.lower().startswith(q), len(p)))
        return [{"name": Path(p).name, "path": p, "dir": os.path.isdir(p)} for p in hits[:8]]
