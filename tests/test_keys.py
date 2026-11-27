"""Windows-Tastenkürzel: werden erkannt und nicht an Programme weitergegeben."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtCore = pytest.importorskip("PySide6.QtCore")
from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QKeyEvent, QWindow  # noqa: E402

from glimra_shell.keys import KeyWatcher  # noqa: E402


@pytest.fixture(scope="module")
def win():
    app = QGuiApplication.instance() or QGuiApplication([])
    w = QWindow()
    yield w
    del app


def press(watcher, win, key, mods=Qt.NoModifier, release=False):
    ev = QKeyEvent(QEvent.KeyRelease if release else QEvent.KeyPress, key, mods)
    return watcher.eventFilter(win, ev)


def test_win_shortcuts(win):
    got = []
    kw = KeyWatcher(got.append)
    assert press(kw, win, Qt.Key_E, Qt.MetaModifier) is True
    assert press(kw, win, Qt.Key_Tab, Qt.AltModifier) is True
    assert press(kw, win, Qt.Key_S, Qt.MetaModifier | Qt.ShiftModifier) is True
    assert press(kw, win, Qt.Key_Escape, Qt.ControlModifier | Qt.ShiftModifier) is True
    assert got == ["files", "alttab", "screenshot", "taskman"]


def test_windows_key_alone_opens_start(win):
    got = []
    kw = KeyWatcher(got.append)
    press(kw, win, Qt.Key_Meta)
    press(kw, win, Qt.Key_Meta, release=True)
    assert got == ["start"]


def test_windows_key_combo_does_not_open_start(win):
    got = []
    kw = KeyWatcher(got.append)
    press(kw, win, Qt.Key_Meta)
    press(kw, win, Qt.Key_L, Qt.MetaModifier)
    press(kw, win, Qt.Key_Meta, release=True)
    assert got == ["lock"]


def test_normal_keys_pass_through(win):
    got = []
    kw = KeyWatcher(got.append)
    assert press(kw, win, Qt.Key_A) is False
    assert press(kw, win, Qt.Key_C, Qt.ControlModifier) is False
    assert got == []
