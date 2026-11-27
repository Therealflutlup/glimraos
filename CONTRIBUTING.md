# Mitmachen

Danke, dass du Glimra OS verbessern willst!

## Entwicklungsumgebung

```bash
python3 -m pip install PySide6 pytest ruff
python3 -m glimra_shell --preview        # im Ordner shell/: Oberfläche als Fenster
python3 -m pytest                       # alle Tests
ruff check .                            # Code-Stil
```

- Symbole ändern: `branding/make_icons.py` bearbeiten und ausführen (keine Emojis in der Oberfläche).
- PNG/ICO für Windows neu erzeugen: `QT_QPA_PLATFORM=offscreen python3 branding/make_png_assets.py`.
- ISO lokal bauen (Arch Linux): `sudo ./build.sh desktop`.

## Regeln

- Oberfläche und Meldungen auf Deutsch, verständlich für Einsteiger.
- Neue Funktionen bekommen Tests, wenn sie ohne Bildschirm testbar sind.
- Ein Pull Request = ein Thema. Beschreibe, wie du getestet hast.
- Mit einem Beitrag stimmst du zu, dass er unter der GPL-3.0 veröffentlicht wird.

## Version veröffentlichen

```bash
python3 tools/bump_version.py 1.1.0   # Version überall setzen
# CHANGELOG.md ergänzen (Abschnitt [1.1.0])
git commit -am "Glimra OS 1.1.0" && git tag v1.1.0 && git push --follow-tags
```
GitHub baut dann ISO, APK und EXE und erstellt das Release mit Prüfsummen.
