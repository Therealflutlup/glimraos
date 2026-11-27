"""Glimra Assistent – versteht einfache deutsche Befehle (getippt oder gesprochen).

Sprache wird offline mit Vosk erkannt (Profil „Assistent“ installiert Vosk + deutsches Modell).
Antworten werden mit espeak-ng vorgelesen, falls installiert.
"""

from __future__ import annotations

import ast
import json
import operator
import random
import re
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path

MODEL_DIR = Path("/usr/share/glimra/vosk-model-de")

APP_WORDS = {
    "settings": ["einstellung", "einstellungen", "optionen"],
    "tools": ["tools", "netzwerk-tools", "werkzeuge"],
    "taskman": ["taskmanager", "task-manager", "prozesse"],
    "wallpaper": ["hintergrund", "hintergrundbild"],
    "terminal": ["terminal", "konsole", "kommandozeile"],
    "browser": ["browser", "firefox", "internet"],
    "files": ["dateien", "dateimanager", "explorer", "ordner"],
    "editor": ["editor", "texteditor", "notizen"],
    "steam": ["steam"],
    "mail": ["mail", "e-mail", "email", "thunderbird"],
    "calc": ["rechner", "taschenrechner"],
    "backup": ["backup", "backups", "sicherung", "sicherungen"],
    "security": ["sicherheit", "virenschutz", "firewall"],
    "vm": ["virtuelle", "vm", "virtueller"],
    "transfer": ["umzug", "datenübertragung"],
    "remote": ["handy", "glimraapp", "fernsteuerung"],
    "help": ["hilfe", "support"],
}

JOKES = [
    "Warum mögen Computer keine Strände? Zu viel Sand im Lüfter.",
    "Ich wollte einen Witz über UDP erzählen, aber ich weiß nicht, ob er ankommt.",
    "Es gibt 10 Arten von Menschen: die, die Binär verstehen, und die anderen.",
]

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}


def safe_calc(expr: str) -> float:
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            if isinstance(node.op, ast.Pow) and abs(ev(node.right)) > 100:
                raise ValueError("zu groß")
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("ungültig")
    return ev(ast.parse(expr, mode="eval"))


def words_to_math(text: str) -> str:
    t = text.lower()
    for a, b in (("plus", "+"), ("minus", "-"), ("mal", "*"), ("geteilt durch", "/"), ("durch", "/"),
                 ("hoch", "**"), (",", "."), ("x", "*")):
        t = t.replace(a, f" {b} ")
    return re.sub(r"[^0-9+\-*/(). ]", "", t).strip()


class Assistant:
    """ask(text) -> (antwort, aktion, wert). Aktionen führt die Shell aus."""

    def __init__(self, info_provider):
        self.info = info_provider  # Funktion -> dict mit ip, hostname

    def voice_available(self) -> bool:
        try:
            import vosk  # noqa: F401
        except ImportError:
            return False
        return MODEL_DIR.exists() and bool(shutil.which("pw-record") or shutil.which("arecord"))

    def listen(self, seconds: int = 5) -> str:
        """Nimmt einige Sekunden über das Mikrofon auf und gibt den erkannten Text zurück."""
        import vosk
        vosk.SetLogLevel(-1)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav = tmp.name
        if shutil.which("pw-record"):
            cmd = ["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16", wav]
        else:
            cmd = ["arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", wav]
        p = subprocess.Popen(cmd)
        time.sleep(seconds)
        p.terminate()
        p.wait(timeout=3)
        model = vosk.Model(str(MODEL_DIR))
        with wave.open(wav, "rb") as wf:
            rec = vosk.KaldiRecognizer(model, wf.getframerate())
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                rec.AcceptWaveform(data)
            text = json.loads(rec.FinalResult()).get("text", "")
        Path(wav).unlink(missing_ok=True)
        return text

    @staticmethod
    def speak(text: str) -> None:
        if shutil.which("espeak-ng"):
            subprocess.Popen(["espeak-ng", "-v", "de", "-s", "165", text],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def ask(self, text: str) -> tuple[str, str, str]:
        t = text.lower().strip().rstrip("?!.")
        if not t:
            return "Ich höre zu – sag zum Beispiel „Öffne den Browser“.", "", ""

        if re.search(r"\b(öffne|starte|zeig|zeige|mach .* auf)\b", t):
            for app, words in APP_WORDS.items():
                if any(w in t for w in words):
                    return "Okay, ich öffne das.", "open", app
        if re.search(r"\b(sperr|sperre|sperren)\b", t):
            return "Ich sperre den Bildschirm.", "lock", ""
        if re.search(r"(ausschalten|herunterfahren|fahr .* runter)", t):
            return "Soll ich den PC wirklich ausschalten?", "confirm", "poweroff"
        if re.search(r"(neu starten|neustart)", t):
            return "Soll ich den PC wirklich neu starten?", "confirm", "reboot"
        if "wie spät" in t or "uhrzeit" in t or "wie viel uhr" in t:
            return f"Es ist {time.strftime('%H:%M')} Uhr.", "", ""
        if "datum" in t or "welcher tag" in t or "welches datum" in t:
            tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            return f"Heute ist {tage[time.localtime().tm_wday]}, der {time.strftime('%d.%m.%Y')}.", "", ""
        if "ip" in t.split() or "ip-adresse" in t or "ip adresse" in t:
            return f"Deine IP-Adresse ist {self.info().get('ip', 'unbekannt')}.", "", ""
        if "lauter" in t:
            return "Lauter.", "volume", "up"
        if "leiser" in t:
            return "Leiser.", "volume", "down"
        if "stumm" in t or "ton aus" in t:
            return "Ton aus.", "volume", "mute"
        m = re.search(r"hintergrund\w* (?:auf |zu )?(aurora|ozean|wald|nacht|sonnenuntergang|automatisch)", t)
        if m:
            key = {"ozean": "ocean", "wald": "forest", "nacht": "night", "sonnenuntergang": "sunset",
                   "automatisch": "auto"}.get(m.group(1), m.group(1))
            return f"Hintergrund ist jetzt {m.group(1).capitalize()}.", "wallpaper", key
        m = re.match(r"(?:suche|such|google)(?: nach)? (.+)", t)
        if m:
            return f"Ich suche nach „{m.group(1)}“.", "search", m.group(1)
        if t.startswith(("rechne", "was ist", "wie viel ist")) or re.fullmatch(r"[0-9+\-*/(). ]+", t):
            expr = words_to_math(re.sub(r"^(rechne|was ist|wie viel ist)", "", t))
            try:
                result = safe_calc(expr)
                txt = str(int(result)) if float(result).is_integer() else f"{result:.6g}".replace(".", ",")
                return f"Das ergibt {txt}.", "", ""
            except (ValueError, ZeroDivisionError, SyntaxError, TypeError):
                pass
        if "witz" in t:
            return random.choice(JOKES), "", ""
        if re.search(r"(wer bist du|wie heißt du)", t):
            return "Ich bin der Glimra Assistent, eingebaut in Glimra OS.", "", ""
        if re.search(r"(was kannst du|hilfe)", t):
            return ("Ich kann Apps öffnen, die Uhrzeit und das Datum sagen, rechnen, im Internet suchen, "
                    "den Bildschirm sperren, die Lautstärke ändern und den Hintergrund wechseln."), "", ""
        return "Das habe ich leider nicht verstanden. Frag mich „Was kannst du?“.", "", ""
