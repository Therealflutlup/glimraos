import re

from conftest import ROOT


def version():
    return (ROOT / "VERSION").read_text().strip()


def test_version_format():
    assert re.fullmatch(r"\d+\.\d+\.\d+", version())


def test_all_parts_same_version():
    import glimra_panel
    import glimra_setup
    import glimra_shell
    for mod in (glimra_shell, glimra_panel, glimra_setup):
        assert mod.__version__ == version(), mod.__name__


def test_changelog_has_current_version():
    assert f"## [{version()}]" in (ROOT / "CHANGELOG.md").read_text()


def test_android_reads_version_file():
    assert 'rootProject.file("../VERSION")' in (ROOT / "android/app/build.gradle.kts").read_text()
