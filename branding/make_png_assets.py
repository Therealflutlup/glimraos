"""Rendert Logo und Symbole als PNG/ICO für den Windows-Setup-Manager.
  QT_QPA_PLATFORM=offscreen python3 branding/make_png_assets.py
"""
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "shell/glimra_shell/qml/Glimra/icons"
LOGO = ROOT / "shell/glimra_shell/assets/glimra.svg"
OUT = ROOT / "windows/glimra_setup/assets"


def render(svg: Path, size: int, dest: Path) -> None:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(str(svg)).render(p, QRectF(0, 0, size, size))
    p.end()
    img.save(str(dest))


def main() -> None:
    app = QGuiApplication(sys.argv)  # noqa: F841
    OUT.mkdir(parents=True, exist_ok=True)
    render(LOGO, 96, OUT / "logo.png")
    render(LOGO, 256, OUT / "logo256.png")
    for name in ("computer", "download", "drive", "transfer", "check", "info", "folder", "network", "chevron", "close"):
        render(ICONS / f"{name}.svg", 26, OUT / f"{name}.png")
    Image.open(OUT / "logo256.png").save(OUT / "glimra.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("PNG/ICO geschrieben:", OUT)


if __name__ == "__main__":
    main()
