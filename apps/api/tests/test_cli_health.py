"""`python -m alfred --health` — the health_check_command in agent.yaml.

Runs as a real subprocess (not an in-process import) because the whole point
is that it works with no server running and no test client wiring: exactly
what an external orchestrator would invoke.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent


def test_health_cli_prints_valid_json_and_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "alfred", "--health"],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert "version" in payload
    assert payload["llm"] in {"online", "offline"}
    assert "db" in payload and "connected" in payload["db"]
    assert "usage_today" in payload
    assert "vault" in payload
