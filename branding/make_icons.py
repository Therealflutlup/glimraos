"""Erzeugt das Glimra-Symbolset (eigene Icons, keine Emojis).

Alle Symbole: 24x24-Raster, Linien 1.8 px, runde Enden.
  python3 branding/make_icons.py
schreibt die SVGs in die Shell, die GlimraApp und den Setup-Manager.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / "shell/glimra_shell/qml/Glimra/icons",
    ROOT / "android/app/src/main/assets/icons",
    ROOT / "panel/glimra_panel/static/icons",
]
STROKE = "#eef1fb"

ICONS = {
    # System
    "settings": '<circle cx="12" cy="12" r="3.2"/><circle cx="12" cy="12" r="7.2" stroke-width="3.2" stroke-dasharray="2.6 3.05"/><circle cx="12" cy="12" r="6"/>',
    "tools": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.1L4.5 16.2a1.6 1.6 0 0 0 2.3 2.3l4.8-4.8a4 4 0 0 0 5.1-5.4l-2.4 2.4-2.1-.3-.3-2.1z"/>',
    "taskman": '<path d="M4 20h16"/><path d="M7 16v-5M12 16V6M17 16v-8"/>',
    "image": '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><circle cx="9" cy="10" r="1.6"/><path d="M4 17l5-4.5 3.5 3 3-2.5 4.5 4"/>',
    "terminal": '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="M7 10l3 2.5L7 15M12.5 15.5h4.5"/>',
    "browser": '<circle cx="12" cy="12" r="8.5"/><ellipse cx="12" cy="12" rx="3.6" ry="8.5"/><path d="M3.8 9h16.4M3.8 15h16.4"/>',
    "folder": '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2.2h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    "file": '<path d="M7 3.5h6.5L18 8v11a1.5 1.5 0 0 1-1.5 1.5h-9.5A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5z"/><path d="M13 3.8V8.5h4.7"/>',
    "script": '<path d="M7 3.5h6.5L18 8v11a1.5 1.5 0 0 1-1.5 1.5h-9.5A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5z"/><path d="M10 12l-2 2 2 2M14 12l2 2-2 2"/>',
    "windowsapp": '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    "editor": '<path d="M5 19l1-4.2L15.6 5.2a1.8 1.8 0 0 1 2.6 0l.6.6a1.8 1.8 0 0 1 0 2.6L9.2 18 5 19z"/><path d="M13.8 7l3.2 3.2"/>',
    "game": '<path d="M7.5 7.5h9a4.5 4.5 0 0 1 4.3 5.8l-1 3.3a2.3 2.3 0 0 1-4 .8L14.4 16H9.6l-1.4 1.4a2.3 2.3 0 0 1-4-.8l-1-3.3a4.5 4.5 0 0 1 4.3-5.8z"/><path d="M8 10.5v3M6.5 12h3"/><circle cx="15.5" cy="11" r=".6" fill="#eef1fb"/><circle cx="17" cy="13" r=".6" fill="#eef1fb"/>',
    "power": '<path d="M12 3.5v8"/><path d="M7 6.5a7 7 0 1 0 10 0"/>',
    "reboot": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4.5H15"/>',
    "moon": '<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>',
    "user": '<circle cx="12" cy="8.5" r="3.8"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>',
    "network": '<circle cx="12" cy="5.5" r="2"/><circle cx="5.5" cy="18" r="2"/><circle cx="18.5" cy="18" r="2"/><path d="M11 7.3L6.5 16.2M13 7.3l4.5 8.9M7.5 18h9"/>',
    "plug": '<path d="M9 3.5v4M15 3.5v4"/><path d="M6.5 7.5h11v3a5.5 5.5 0 0 1-11 0z"/><path d="M12 16v4.5"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/><path d="M12 14.5v2"/>',
    "mail": '<rect x="3.5" y="5.5" width="17" height="13" rx="2.5"/><path d="M4.5 7.5l7.5 5.5 7.5-5.5"/>',
    "vm": '<rect x="3" y="4" width="18" height="12.5" rx="2"/><rect x="8" y="7.5" width="8" height="5.5" rx="1"/><path d="M9 20h6M12 16.5V20"/>',
    "backup": '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/><path d="M4.5 4.5V9H9"/><path d="M12 8v4.3l3 1.8"/>',
    "shield": '<path d="M12 3.5l7 2.8v5.2c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6.3z"/><path d="M9 12l2.2 2.2L15.5 10"/>',
    "phone": '<rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="M11 18h2"/>',
    "mic": '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M6 11.5a6 6 0 0 0 12 0M12 17.5v3"/>',
    "transfer": '<path d="M4 8.5h14l-3.5-3.5M20 15.5H6l3.5 3.5"/>',
    "help": '<circle cx="12" cy="12" r="8.5"/><path d="M9.7 9.5a2.4 2.4 0 1 1 3.3 2.2c-.6.3-1 .8-1 1.5v.5"/><circle cx="12" cy="16.6" r=".7" fill="#eef1fb"/>',
    "calc": '<rect x="5" y="3" width="14" height="18" rx="2.5"/><rect x="8" y="6" width="8" height="3.5" rx=".8"/><path d="M8.5 13h.01M12 13h.01M15.5 13h.01M8.5 16.5h.01M12 16.5h.01M15.5 16.5h.01" stroke-width="2.4"/>',
    "assistant": '<path d="M12 3.5l1.9 4.6 4.6 1.9-4.6 1.9L12 16.5l-1.9-4.6L5.5 10l4.6-1.9z"/><path d="M18 15.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z"/>',
    "sparkle": '<path d="M12 3l2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2z"/>',
    "bolt": '<path d="M13 3L5.5 13.5H12L11 21l7.5-10.5H12z"/>',
    "briefcase": '<rect x="3.5" y="7.5" width="17" height="12" rx="2.5"/><path d="M9 7.5V6a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 6v1.5M3.5 12.5h17"/>',
    "apps": '<rect x="4" y="4" width="6.5" height="6.5" rx="1.8"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.8"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.8"/><circle cx="16.75" cy="16.75" r="3.3"/>',
    "close": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "minimize": '<path d="M6 12h12"/>',
    "maximize": '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
    "restore": '<rect x="5.5" y="8.5" width="10" height="10" rx="1.5"/><path d="M8.5 8.5V6.5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-2"/>',
    "refresh": '<path d="M19.5 12a7.5 7.5 0 0 1-13.1 5M4.5 12a7.5 7.5 0 0 1 13.1-5"/><path d="M17.8 3.5v3.6h-3.6M6.2 20.5v-3.6h3.6"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "trash": '<path d="M4.5 7h15M9.5 7V4.8h5V7M6.5 7l1 12.5h9l1-12.5M10 10.5v6M14 10.5v6"/>',
    "download": '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
    "upload": '<path d="M12 15V4M7.5 8.5L12 4l4.5 4.5M5 19.5h14"/>',
    "clipboard": '<rect x="5.5" y="5" width="13" height="16" rx="2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 15.5h4"/>',
    "send": '<path d="M4 12l16-7.5-5.5 15.5-3-6.5z"/><path d="M11.5 13.5L20 4.5"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "play": '<path d="M8 5.5v13l10.5-6.5z"/>',
    "stop": '<rect x="6.5" y="6.5" width="11" height="11" rx="1.5"/>',
    "drive": '<rect x="3.5" y="13" width="17" height="6.5" rx="2"/><path d="M5.5 13l2.5-7.5h8L18.5 13M16.5 16.3h.01" stroke-linejoin="round"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r=".7" fill="#eef1fb"/>',
    "palette": '<path d="M12 3.5a8.5 8.5 0 0 0 0 17c1.2 0 1.8-.8 1.8-1.7 0-1.2-1-1.5-1-2.6 0-1 .8-1.7 1.8-1.7h2a3.9 3.9 0 0 0 3.9-3.9C20.5 6.8 16.7 3.5 12 3.5z"/><circle cx="8" cy="11" r=".9" fill="#eef1fb"/><circle cx="10.5" cy="7.5" r=".9" fill="#eef1fb"/><circle cx="14.5" cy="7.5" r=".9" fill="#eef1fb"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="#eef1fb"/>',
    "computer": '<rect x="3" y="4.5" width="18" height="12" rx="2"/><path d="M8.5 20h7M12 16.5V20"/>',
    "volume": '<path d="M4.5 9.5h3.5L12.5 5.5v13L8 14.5H4.5z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
    "wifi": '<path d="M3.5 9.5a12 12 0 0 1 17 0M6.5 12.7a7.5 7.5 0 0 1 11 0M9.5 15.8a3.2 3.2 0 0 1 5 0"/><circle cx="12" cy="18.8" r=".9" fill="#eef1fb"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="M11 12l8.5-8.5M16 7l2.5 2.5M14 9l2 2"/>',
    "bluetooth": '<path d="M7 7.5l10 9-5 4.5V3l5 4.5-10 9"/>',
    "battery": '<rect x="3" y="7.5" width="16" height="9" rx="2"/><path d="M21 10.5v3"/><rect x="5.5" y="10" width="7" height="4" rx=".6" fill="#eef1fb" stroke="none"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.8v2.2M12 19v2.2M2.8 12h2.2M19 12h2.2M5.5 5.5l1.6 1.6M16.9 16.9l1.6 1.6M5.5 18.5l1.6-1.6M16.9 7.1l1.6-1.6"/>',
    "plane": '<path d="M10.5 3.8c0-1 .7-1.6 1.5-1.6s1.5.6 1.5 1.6v5.4l7 4.3v2l-7-2.2v4.4l2.2 1.7v1.8L12 20.4l-3.7.8v-1.8l2.2-1.7v-4.4l-7 2.2v-2l7-4.3z"/>',
    "bag": '<path d="M5 8h14l-1.2 11.2a1.8 1.8 0 0 1-1.8 1.6H8a1.8 1.8 0 0 1-1.8-1.6z"/><path d="M9 10V7a3 3 0 0 1 6 0v3"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "camera": '<path d="M4 8.5a2 2 0 0 1 2-2h2l1.5-2h5L16 6.5h2a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><circle cx="12" cy="12.5" r="3.5"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "update": '<path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5"/><path d="M12 8v6M9 11l3 3 3-3"/><path d="M17 3.5h3.5V7"/>',
    "desktop": '<rect x="3" y="4.5" width="18" height="12" rx="2"/><path d="M3 13h18M8.5 20h7M12 16.5V20"/>',
    "snap": '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M12 4.5v15M12 12h8.5"/>',
    "chevron": '<path d="M9.5 6l6 6-6 6"/>',
}


def svg(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" '
        f'fill="none" stroke="{STROKE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>\n"
    )


def main() -> None:
    for target in TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        for name, body in ICONS.items():
            (target / f"{name}.svg").write_text(svg(body), encoding="utf-8")
    print(f"{len(ICONS)} Symbole in {len(TARGETS)} Ordner geschrieben.")


if __name__ == "__main__":
    main()
