"""Leistung: Die Shell soll sparsam bleiben (Vorschau-Modus, ohne Grafikkarte gemessen)."""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import ROOT

pytest.importorskip("PySide6")
LIMIT_MB = 180        # Grenze für den Arbeitsspeicher der Shell im Leerlauf
CPU_LIMIT = 2.0       # Prozent CPU im Leerlauf


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="misst über /proc")
def test_shell_idle_memory_and_cpu(tmp_path):
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "HOME": str(tmp_path), "MALLOC_ARENA_MAX": "2"}
    (tmp_path / ".config/glimra").mkdir(parents=True)
    (tmp_path / ".config/glimra/settings.json").write_text('{"setupDone": true, "name": "Test"}')
    p = subprocess.Popen([sys.executable, "-m", "glimra_shell", "--preview"], cwd=ROOT / "shell", env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(6)
        assert p.poll() is None, "Shell ist abgestürzt"
        stat = Path(f"/proc/{p.pid}/stat")
        t1 = sum(int(x) for x in stat.read_text().split()[13:15])
        time.sleep(5)
        t2 = sum(int(x) for x in stat.read_text().split()[13:15])
        rss = int(next(line for line in Path(f"/proc/{p.pid}/status").read_text().splitlines()
                       if line.startswith("VmRSS")).split()[1]) / 1024
        cpu = (t2 - t1) / os.sysconf("SC_CLK_TCK") / 5 * 100
        print(f"Shell: {rss:.0f} MB, CPU {cpu:.2f} %")
        assert rss < LIMIT_MB, f"Shell braucht {rss:.0f} MB (Grenze {LIMIT_MB} MB)"
        assert cpu < CPU_LIMIT, f"Shell braucht im Leerlauf {cpu:.1f} % CPU"
    finally:
        p.kill()
