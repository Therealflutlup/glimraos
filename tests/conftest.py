import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for sub in ("shell", "panel", "windows"):
    sys.path.insert(0, str(ROOT / sub))


@pytest.fixture
def free_port():
    def get() -> int:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port
    return get
