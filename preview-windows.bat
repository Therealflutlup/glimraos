@echo off
REM Startet die Glimra Shell als Vorschau-Fenster unter Windows.
cd /d "%~dp0shell"
python -m pip install --quiet PySide6
python -m glimra_shell --preview
pause
