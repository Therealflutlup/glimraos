#!/usr/bin/env bash
# Startet die Glimra Shell als Vorschau-Fenster unter Linux.
cd "$(dirname "$0")/shell" || exit 1
python3 -m pip install --user --quiet PySide6 2>/dev/null || true
python3 -m glimra_shell --preview
