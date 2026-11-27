import subprocess

from glimra_shell import devices, store


def fake_run(outputs):
    def run(cmd, timeout=8):
        key = " ".join(cmd[:3])
        for k, v in outputs.items():
            if key.startswith(k):
                return subprocess.CompletedProcess(cmd, 0, v, "")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return run


def test_parse_pacman_search():
    out = ("extra/vlc 3.0.21-1\n    Multi-platform MPEG, VCD/DVD, and DivX player\n"
           "extra/vlc-plugins 3.0.21-1 [installiert]\n    Plugins\n")
    res = store.parse_pacman_search(out)
    assert [r["id"] for r in res] == ["vlc", "vlc-plugins"]
    assert res[0]["desc"].startswith("Multi") and res[1]["installed"]


def test_package_name_validation():
    assert not store.install("vlc; rm -rf /")[0]
    assert not store.remove("../etc")[0]
    assert store.PKG_RE.match("flatpak:com.discordapp.Discord")


def test_search_rejects_strange_input():
    assert store.search("a") == [] and store.search("$(reboot)") == []


def test_volume(monkeypatch):
    monkeypatch.setattr(devices, "has", lambda t: True)
    monkeypatch.setattr(devices, "_run", fake_run({"wpctl get-volume": "Volume: 0.45 [MUTED]\n"}))
    assert devices.volume() == {"level": 45, "muted": True, "available": True}


def test_wifi_list(monkeypatch):
    monkeypatch.setattr(devices, "has", lambda t: True)
    out = "*:FritzBox 7590:80:WPA2\n:Nachbar:40:WPA2\n:Cafe\\:Gast:60:\n:FritzBox 7590:30:WPA2\n"
    monkeypatch.setattr(devices, "_run", fake_run({"nmcli -t -f": out}))
    nets = devices.wifi_list()
    assert [n["ssid"] for n in nets] == ["FritzBox 7590", "Cafe:Gast", "Nachbar"]
    assert nets[0]["active"] and not nets[1]["secure"]


def test_bt_connect_validates_mac():
    assert devices.bt_connect("nicht; reboot")[0] is False


def test_featured_has_unique_ids():
    ids = [f["id"] for f in store.FEATURED]
    assert len(ids) == len(set(ids)) and all(store.PKG_RE.match(i) for i in ids)
