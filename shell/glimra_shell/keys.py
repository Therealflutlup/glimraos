"""Globale Tastenkürzel wie bei Windows.

Fängt die Tasten ab, bevor sie an Programme gehen – so funktionieren Win+E, Alt+Tab usw.
auch, wenn gerade Firefox oder ein Spiel den Fokus hat. Die Windows-Taste allein öffnet das Startmenü.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QWindow

META_KEYS = {Qt.Key_Meta, Qt.Key_Super_L, Qt.Key_Super_R}

WIN_SHORTCUTS = {
    Qt.Key_E: "files", Qt.Key_L: "lock", Qt.Key_D: "desktop", Qt.Key_I: "settings",
    Qt.Key_A: "quick", Qt.Key_N: "notifications", Qt.Key_V: "clipboard", Qt.Key_S: "search",
    Qt.Key_R: "terminal", Qt.Key_Up: "snap-up", Qt.Key_Down: "snap-down",
    Qt.Key_Left: "snap-left", Qt.Key_Right: "snap-right", Qt.Key_Tab: "alttab",
}

# Übersicht für Einstellungen → Tastenkürzel
HELP = [
    ("Windows-Taste", "Startmenü öffnen"), ("Win + E", "Dateien"), ("Win + I", "Einstellungen"),
    ("Win + L", "Sperren"), ("Win + D", "Desktop anzeigen"), ("Win + A", "Schnelleinstellungen"),
    ("Win + N", "Info-Center"), ("Win + V", "Zwischenablage-Verlauf"), ("Win + S", "Suchen"),
    ("Win + R", "Terminal"), ("Win + Pfeiltasten", "Fenster andocken"), ("Alt + Tab", "Fenster wechseln"),
    ("Alt + F4", "Fenster schließen"), ("Druck / Win + Umschalt + S", "Bildschirmfoto"),
    ("Strg + Umschalt + Esc", "Taskmanager"),
]


class KeyWatcher(QObject):
    def __init__(self, emit):
        super().__init__()
        self._emit = emit          # Funktion(name)
        self._meta_alone = False

    def eventFilter(self, obj, ev):  # noqa: N802 – Qt-Name
        if not isinstance(obj, QWindow):
            return False
        t = ev.type()
        if t == QEvent.KeyPress:
            key, mods = ev.key(), ev.modifiers()
            if key in META_KEYS:
                self._meta_alone = not ev.isAutoRepeat()
                return False
            self._meta_alone = False
            name = None
            if mods & Qt.MetaModifier:
                name = "screenshot" if (key == Qt.Key_S and mods & Qt.ShiftModifier) else WIN_SHORTCUTS.get(key)
            elif mods & Qt.AltModifier and key == Qt.Key_Tab:
                name = "alttab"
            elif mods & Qt.AltModifier and key == Qt.Key_F4:
                name = "close"
            elif key == Qt.Key_Print:
                name = "screenshot"
            elif key == Qt.Key_Escape and mods & Qt.ControlModifier and mods & Qt.ShiftModifier:
                name = "taskman"
            if name:
                self._emit(name)
                return True     # Programme bekommen das Kürzel nicht
        elif t == QEvent.KeyRelease and ev.key() in META_KEYS and not ev.isAutoRepeat():
            if self._meta_alone:
                self._emit("start")
            self._meta_alone = False
        return False
