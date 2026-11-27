import pytest
from glimra_shell.assistant import Assistant, safe_calc

A = Assistant(lambda: {"ip": "192.168.178.20"})


@pytest.mark.parametrize("text,action,value", [
    ("Öffne den Browser", "open", "browser"),
    ("starte die Einstellungen", "open", "settings"),
    ("sperre den PC", "lock", ""),
    ("Hintergrund auf Ozean", "wallpaper", "ocean"),
    ("suche Minecraft Mods", "search", "minecraft mods"),
    ("ausschalten", "confirm", "poweroff"),
    ("mach lauter", "volume", "up"),
])
def test_actions(text, action, value):
    _, a, v = A.ask(text)
    assert (a, v) == (action, value)


@pytest.mark.parametrize("text,expected", [
    ("rechne 5 mal 3 plus 2", "17"),
    ("was ist 7 geteilt durch 2", "3,5"),
    ("12*4", "48"),
])
def test_math(text, expected):
    assert expected in A.ask(text)[0]


def test_ip():
    assert "192.168.178.20" in A.ask("meine IP?")[0]


def test_unknown():
    assert "nicht verstanden" in A.ask("blablabla")[0]


@pytest.mark.parametrize("bad", ["__import__('os')", "2**999999", "open('x')", "a+1"])
def test_safe_calc_rejects(bad):
    with pytest.raises((ValueError, SyntaxError)):
        safe_calc(bad)
