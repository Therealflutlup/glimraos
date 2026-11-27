import shutil
import subprocess

import pytest
from conftest import ROOT

SCRIPTS = sorted([*ROOT.glob("profiles/*/airootfs/usr/local/bin/*"), ROOT / "build.sh",
                  *ROOT.glob("tools/*.sh"), *ROOT.glob("profiles/*/airootfs/etc/profile.d/*.sh")])


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_bash_syntax(script):
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck fehlt")
def test_shellcheck():
    res = subprocess.run(["shellcheck", "-S", "warning", *map(str, SCRIPTS)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout


def test_sudoers_only_glimra_helpers():
    text = (ROOT / "profiles/common/airootfs/etc/sudoers.d/20-glimra").read_text()
    import re
    paths = re.findall(r"(/[\w/.-]+)", text)
    assert paths and all(p.startswith("/usr/local/bin/glimra-") or p == "/etc/sudoers.d/20-glimra" for p in paths), paths
    assert "ALL=(ALL" not in text
