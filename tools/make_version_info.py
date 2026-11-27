"""Schreibt windows/version_info.txt (Versionsangaben für GlimraSetup.exe) aus der Datei VERSION."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
v = (ROOT / "VERSION").read_text().strip()
t = tuple(int(x) for x in v.split(".")) + (0,)
(ROOT / "windows" / "version_info.txt").write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040704B0', [
      StringStruct('CompanyName', 'Glimra OS'),
      StringStruct('FileDescription', 'Glimra Setup-Manager'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'GlimraSetup'),
      StringStruct('LegalCopyright', 'Glimra OS – GNU GPL v3'),
      StringStruct('OriginalFilename', 'GlimraSetup.exe'),
      StringStruct('ProductName', 'Glimra OS'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1031, 1200])])
  ]
)
""", encoding="utf-8")
print("version_info.txt für", v)
