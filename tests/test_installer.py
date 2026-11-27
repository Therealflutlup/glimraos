"""Tests für den grafischen Installer (Vollversion vom USB-Stick installieren)."""

import re
import stat
import subprocess
from pathlib import Path

import pytest

from glimra_shell import installer

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "profiles/common/airootfs/usr/local/bin/glimra-install"

LSBLK = {"blockdevices": [
    {"name": "loop0", "path": "/dev/loop0", "size": 900000000, "model": None, "type": "loop", "tran": None, "rm": False},
    {"name": "sda", "path": "/dev/sda", "size": 500107862016, "model": "Samsung SSD 870", "type": "disk", "tran": "sata", "rm": False},
    {"name": "sdb", "path": "/dev/sdb", "size": 31037849600, "model": "SanDisk 3.2Gen1", "type": "disk", "tran": "usb", "rm": True},
    {"name": "sdc", "path": "/dev/sdc", "size": 8004304896, "model": "Mini", "type": "disk", "tran": "usb", "rm": True},
    {"name": "sr0", "path": "/dev/sr0", "size": 1073741312, "model": "DVD", "type": "rom", "tran": "sata", "rm": True},
    {"name": "zram0", "path": "/dev/zram0", "size": 4000000000, "model": None, "type": "disk", "tran": None, "rm": False},
]}


def test_parse_lsblk_filters_and_marks_boot_stick():
    disks = installer.decorate(installer.parse_lsblk(LSBLK, boot_disk="/dev/sdb"))
    paths = [d["path"] for d in disks]
    assert paths[0] == "/dev/sda"                        # interne Platte zuerst
    assert "/dev/loop0" not in paths and "/dev/sr0" not in paths and "/dev/zram0" not in paths
    by = {d["path"]: d for d in disks}
    assert by["/dev/sda"]["usable"] and by["/dev/sda"]["kind"] == "SATA"
    assert not by["/dev/sdb"]["usable"] and "gerade" in by["/dev/sdb"]["problem"]
    assert not by["/dev/sdc"]["usable"] and "klein" in by["/dev/sdc"]["problem"]
    assert by["/dev/sdb"]["removable"]


def test_human_size():
    assert installer.human_size(500107862016) == "500,1 GB"
    assert installer.human_size(1000204886016) == "1,0 TB"


@pytest.mark.parametrize("args,ok", [
    (("leon-pc", "leon", "geheim", "geheim", "", "desktop"), True),
    (("leon pc", "leon", "x", "x", "", "desktop"), False),
    (("pc", "Leon", "x", "x", "", "desktop"), False),
    (("pc", "leon", "", "", "", "desktop"), False),
    (("pc", "leon", "a", "b", "", "desktop"), False),
    (("pc", "leon", "a\nb", "a\nb", "", "desktop"), False),
    (("pc", "leon", "a", "a", "kurz", "server"), False),
    (("pc", "leon", "a", "a", "langgenug", "server"), True),
])
def test_validate(args, ok):
    assert (installer.validate(*args) == "") is ok


def test_parse_line():
    assert installer.parse_line("@@STEP 3 6 Pakete installieren\n") == ("step", (3, 6, "Pakete installieren"))
    assert installer.parse_line("@@ERROR Keine Internetverbindung") == ("error", "Keine Internetverbindung")
    assert installer.parse_line("@@DONE\n") == ("done", "")
    assert installer.parse_line("downloading linux...") == ("log", "downloading linux...")


def test_run_install_with_fake_tool(tmp_path, monkeypatch):
    fake = tmp_path / "glimra-install"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        '[[ $1 == --auto ]] || exit 9\n'
        "IFS= read -r D; IFS= read -r H; IFS= read -r U; IFS= read -r P; IFS= read -r Q || true\n"
        'echo "@@STEP 1 6 Festplatte vorbereiten"\n'
        'echo "disk=$D host=$H user=$U"\n'
        'echo "@@STEP 6 6 Edition einrichten"\n'
        '[[ $P == "pa ss" ]] && echo "@@DONE"\n')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr(installer, "INSTALL_TOOL", str(fake))
    monkeypatch.setattr(installer.os, "geteuid", lambda: 0)
    steps, logs = [], []
    ok, text = installer.run_install("/dev/sda", "pc", "leon", "pa ss", "",
                                     lambda n, t, s: steps.append((n, t, s)), logs.append, tmp_path / "log.txt")
    assert ok, text
    assert steps == [(1, 6, "Festplatte vorbereiten"), (6, 6, "Edition einrichten")]
    assert logs == ["disk=/dev/sda host=pc user=leon"]
    assert "pa ss" not in (tmp_path / "log.txt").read_text()   # Passwort landet nicht im Protokoll


def test_run_install_reports_error(tmp_path, monkeypatch):
    fake = tmp_path / "glimra-install"
    fake.write_text('#!/usr/bin/env bash\ncat >/dev/null\necho "@@ERROR Keine Internetverbindung."\nexit 1\n')
    fake.chmod(0o755)
    monkeypatch.setattr(installer, "INSTALL_TOOL", str(fake))
    monkeypatch.setattr(installer.os, "geteuid", lambda: 0)
    ok, text = installer.run_install("/dev/sda", "pc", "leon", "x", "", lambda *a: None, lambda *a: None)
    assert not ok and text == "Keine Internetverbindung."


def test_install_script_auto_mode_and_labels():
    src = INSTALL.read_text(encoding="utf-8")
    subprocess.run(["bash", "-n", str(INSTALL)], check=True)
    assert "--auto" in src and "@@STEP" in src and "@@DONE" in src and "@@ERROR" in src
    assert "/run/archiso/bootmnt" in src                       # nie auf den Boot-Stick installieren
    # Bezeichnungen mit Leerzeichen ohne Anführungszeichen würden mkfs/sgdisk zerlegen
    assert not re.search(r"-L Glimra OS|-c2:Glimra OS", src)
    assert src.count('step ') >= 6


def test_live_detection(monkeypatch):
    monkeypatch.setenv("GLIMRA_FAKE_LIVE", "1")
    assert installer.is_live()
    monkeypatch.delenv("GLIMRA_FAKE_LIVE")
    assert installer.is_live() == Path("/run/archiso").is_dir()
