"""Glimra Shell – Startpunkt.

  python -m glimra_shell            -> echte Shell (Wayland-Compositor, nur Linux)
  python -m glimra_shell --preview  -> Vorschau als normales Fenster (auch Windows)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QML_DIR = HERE / "qml"
SOCKET = "wayland-glimra"


def main() -> int:
    parser = argparse.ArgumentParser(prog="glimra-shell")
    parser.add_argument("--preview", action="store_true", help="als normales Fenster starten")
    parser.add_argument("--screenshot", metavar="PNG", help="(Test) Bild speichern und beenden")
    parser.add_argument("--app", help="(Test) interne App direkt öffnen")
    args = parser.parse_args()

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    if not args.preview and sys.platform.startswith("linux"):
        # Direkt auf der Grafikkarte zeichnen (ohne X11/anderen Compositor)
        if not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
            os.environ.setdefault("QT_QPA_PLATFORM", "eglfs")
            os.environ.setdefault("QT_QPA_EGLFS_INTEGRATION", "eglfs_kms")
            os.environ.setdefault("QT_QPA_EGLFS_ALWAYS_SET_MODE", "1")
        os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine

    from .backend import Backend

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Glimra Shell")
    app.setOrganizationName("Glimra OS")
    icon = HERE / "assets" / "glimra.svg"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    glimra_mode = not args.preview
    backend = Backend(glimra_mode=glimra_mode, wayland_socket=SOCKET)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("startApp", args.app or "")
    engine.load(QUrl.fromLocalFile(str(QML_DIR / ("preview.qml" if args.preview else "main.qml"))))
    if not engine.rootObjects():
        print("Glimra Shell: QML konnte nicht geladen werden.", file=sys.stderr)
        return 1

    from PySide6.QtQuick import QQuickWindow

    root = engine.rootObjects()[0]
    win = root if isinstance(root, QQuickWindow) else root.findChild(QQuickWindow)
    if win is not None:
        backend.set_window(win)

    from .keys import KeyWatcher

    keys = KeyWatcher(backend.shortcut.emit)
    app.installEventFilter(keys)

    if args.screenshot:
        def shoot():
            win.grabWindow().save(args.screenshot)
            app.quit()

        QTimer.singleShot(1500, shoot)

    ret = app.exec()
    del engine  # Oberfläche vor dem Backend abbauen
    return ret


if __name__ == "__main__":
    sys.exit(main())
