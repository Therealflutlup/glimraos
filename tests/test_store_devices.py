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


def run_map(table):
    """Fake _run: Schlüssel = Anfang des Befehls (ganze Wörter)."""
    def run(cmd, timeout=8):
        line = " ".join(cmd)
        best = max((k for k in table if line.startswith(k)), key=len, default=None)
        return subprocess.CompletedProcess(cmd, 0, table.get(best, ""), "")
    return run


RFKILL_OFF = "wlan blocked unblocked\nbluetooth blocked unblocked\n"
RFKILL_ON = "wlan unblocked unblocked\nbluetooth unblocked unblocked\n"


def test_airplane_uses_rfkill(monkeypatch):
    monkeypatch.setattr(devices, "has", lambda t: True)
    monkeypatch.setattr(devices, "_run", run_map({"rfkill -rn": RFKILL_OFF}))
    assert devices.airplane() is True
    monkeypatch.setattr(devices, "_run", run_map({"rfkill -rn": RFKILL_ON}))
    assert devices.airplane() is False
    monkeypatch.setattr(devices, "_run", run_map({"rfkill -rn": "wlan blocked unblocked\nbluetooth unblocked unblocked\n"}))
    assert devices.airplane() is False                   # nur WLAN aus ist kein Flugmodus


def test_airplane_nmcli_fallback_reads_wifi_column(monkeypatch):
    monkeypatch.setattr(devices, "has", lambda t: t != "rfkill")
    out = "WIFI-HW  WIFI      WWAN-HW  WWAN\nenabled  disabled  missing  enabled\n"
    monkeypatch.setattr(devices, "_run", run_map({"nmcli radio all": out}))
    assert devices.airplane() is True
    out = "WIFI-HW  WIFI     WWAN-HW  WWAN\nenabled  enabled  missing  disabled\n"
    monkeypatch.setattr(devices, "_run", run_map({"nmcli radio all": out}))
    assert devices.airplane() is False                   # früher fälschlich "an" (WWAN-Spalte gelesen)


def test_set_airplane_blocks_all_radios(monkeypatch):
    calls = []
    monkeypatch.setattr(devices, "has", lambda t: True)
    monkeypatch.setattr(devices, "_run", lambda cmd, timeout=8: calls.append(" ".join(cmd)) or subprocess.CompletedProcess(cmd, 0, "", ""))
    devices.set_airplane(True)
    assert "rfkill block all" in calls and "nmcli radio all off" in calls and "bluetoothctl power off" in calls
    calls.clear()
    devices.set_airplane(False)
    assert "rfkill unblock all" in calls and "bluetoothctl power on" in calls


def test_wifi_state_explains_problems(monkeypatch):
    monkeypatch.setattr(devices, "has", lambda t: True)
    monkeypatch.setattr(devices, "_run", run_map({"nmcli -t -f RUNNING": "stopped\n"}))
    st = devices.wifi_state()
    assert not st["available"] and "Netzwerkdienst" in st["note"]

    monkeypatch.setattr(devices, "_run", run_map({"nmcli -t -f RUNNING": "running\n",
                                                  "nmcli -t -f DEVICE,TYPE": "enp3s0:ethernet\nlo:loopback\n"}))
    assert "Kein WLAN-Adapter" in devices.wifi_state()["note"]

    monkeypatch.setattr(devices, "_run", run_map({
        "nmcli -t -f RUNNING": "running\n", "nmcli -t -f DEVICE,TYPE": "wlan0:wifi\n",
        "rfkill -rn": "wlan unblocked blocked\n", "nmcli radio wifi": "enabled\n"}))
    st = devices.wifi_state()
    assert st["available"] and not st["enabled"] and "Schalter" in st["note"]

    monkeypatch.setattr(devices, "_run", run_map({
        "nmcli -t -f RUNNING": "running\n", "nmcli -t -f DEVICE,TYPE": "wlan0:wifi\n",
        "rfkill -rn": RFKILL_ON, "nmcli radio wifi": "enabled\n", "nmcli -t -f ACTIVE,SSID": "no:Nachbar\nyes:FritzBox\n"}))
    assert devices.wifi_state() == {"available": True, "enabled": True, "connected": "FritzBox", "note": ""}


def test_set_wifi_unblocks_rfkill(monkeypatch):
    calls = []
    monkeypatch.setattr(devices, "has", lambda t: True)
    monkeypatch.setattr(devices, "_run", lambda cmd, timeout=8: calls.append(" ".join(cmd)) or subprocess.CompletedProcess(cmd, 0, "", ""))
    devices.set_wifi(True)
    assert calls == ["rfkill unblock wlan", "nmcli radio wifi on"]


def test_live_iso_uses_networkmanager():
    from pathlib import Path
    build = (Path(__file__).resolve().parents[1] / "build.sh").read_text(encoding="utf-8")
    assert "NetworkManager.service" in build and "iwd.service" in build
    pk = (Path(__file__).resolve().parents[1] / "profiles/common/packages.extra").read_text()
    assert "networkmanager" in pk and "wpa_supplicant" in pk
