"""Prüft Oberflächen-Dateien: keine Emojis, alle verwendeten Symbole vorhanden."""
import re

from conftest import ROOT

ICON_DIR = ROOT / "shell/glimra_shell/qml/Glimra/icons"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿]")
UI_FILES = (list((ROOT / "shell/glimra_shell/qml").rglob("*.qml")) + [ROOT / "android/app/src/main/assets/index.html",
            ROOT / "panel/glimra_panel/static/index.html", ROOT / "site/index.html"] + list((ROOT / "windows/glimra_setup").glob("*.py")))


def test_no_emojis():
    for f in UI_FILES:
        hits = EMOJI.findall(f.read_text(encoding="utf-8"))
        assert not hits, f"{f.name}: {hits}"


def test_qml_icons_exist():
    names = set()
    for f in (ROOT / "shell/glimra_shell/qml").rglob("*.qml"):
        names |= set(re.findall(r'\b(?:icon|name|sym|i)\s*:\s*"([a-z]+)"', f.read_text()))
    known = {p.stem for p in ICON_DIR.glob("*.svg")}
    skip = {"profil", "konto", "design", "nutzung", "netz", "system", "ueber", "min", "max", "folder", "lock"}
    missing = {n for n in names if n not in known and n not in skip and not n.startswith(("aurora", "sunset"))}
    # Nur Wörter prüfen, die wie Symbolnamen aussehen und nicht in Datenlisten stehen
    missing -= {"gaming", "leistung", "arbeit", "apps", "ocean", "forest", "night", "auto", "settings"} - known
    assert not missing, missing


def test_html_icons_exist():
    for f in (ROOT / "android/app/src/main/assets/index.html", ROOT / "panel/glimra_panel/static/index.html",
              ROOT / "site/index.html"):
        for n in re.findall(r'icons/([a-z]+)\.svg', f.read_text()):
            assert (f.parent / "icons" / f"{n}.svg").exists(), (f.name, n)


def test_icon_sets_in_sync():
    base = {p.name for p in ICON_DIR.glob("*.svg")}
    for d in (ROOT / "android/app/src/main/assets/icons", ROOT / "panel/glimra_panel/static/icons"):
        assert base <= {p.name for p in d.glob("*.svg")}, d
