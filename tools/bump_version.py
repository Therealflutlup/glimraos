"""Setzt eine neue Versionsnummer in allen Teilen von Glimra OS.
  python3 tools/bump_version.py 1.1.0
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["shell/glimra_shell/__init__.py", "panel/glimra_panel/__init__.py", "windows/glimra_setup/__init__.py"]


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("Nutzung: python3 tools/bump_version.py X.Y.Z")
    v = sys.argv[1]
    (ROOT / "VERSION").write_text(v + "\n")
    for f in FILES:
        p = ROOT / f
        p.write_text(re.sub(r'__version__ = "[^"]+"', f'__version__ = "{v}"', p.read_text()))
    print(f"Version {v} gesetzt. Jetzt CHANGELOG.md ergänzen und mit  git tag v{v}  veröffentlichen.")


if __name__ == "__main__":
    main()
