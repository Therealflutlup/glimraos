import json

import pytest
from glimra_setup import core
from glimra_shell.remote import RemoteServer
from test_remote import FakeBridge


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "win"
    (home / "Documents" / "Schule").mkdir(parents=True)
    (home / "Documents" / "Schule" / "Mathe Test.txt").write_text("hallo")
    (home / "Documents" / "desktop.ini").write_text("x")
    (home / "Pictures").mkdir()
    (home / "Pictures" / "foto.jpg").write_bytes(b"img")
    monkeypatch.setattr(core.Path, "home", lambda: home)
    return home


def test_collect(fake_home, tmp_path):
    files = core.collect(["Dokumente", "Bilder"], tmp_path / "w")
    rels = sorted(r for _, r in files)
    assert rels == ["Bilder/foto.jpg", "Dokumente/Schule/Mathe Test.txt"]


def test_copy_to_folder(fake_home, tmp_path):
    files = core.collect(["Dokumente"], tmp_path / "w")
    assert core.copy_to_folder(files, tmp_path / "usb") == 1
    meta = json.loads((tmp_path / "usb" / "GlimraUmzug" / "glimra-umzug.json").read_text())
    assert meta["dateien"] == 1


def test_send_to_glimra(fake_home, tmp_path, free_port, monkeypatch):
    target_home = tmp_path / "glimra"
    monkeypatch.setattr("pathlib.Path.home", lambda: target_home)
    srv = RemoteServer(FakeBridge(), tmp_path / "cfg", http_port=free_port(), udp_port=free_port())
    srv.start()
    try:
        files = [(fake_home / "Pictures" / "foto.jpg", "Bilder/foto.jpg")]
        with pytest.raises(PermissionError):
            core.send_to_glimra(files, f"127.0.0.1:{srv.http_port}", "999999" if srv.transfer_code != "999999" else "111111")
        assert core.send_to_glimra(files, f"127.0.0.1:{srv.http_port}", srv.transfer_code) == 1
        assert (target_home / "Umzug" / "Bilder" / "foto.jpg").read_bytes() == b"img"
    finally:
        srv.stop()


def test_unreachable():
    with pytest.raises(ConnectionError):
        core.check_glimra("127.0.0.1", 1, "123456")


def test_human():
    assert core.human(1536) == "2 KB" and core.human(5 * 1024 ** 3) == "5.0 GB"
