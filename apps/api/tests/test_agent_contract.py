"""Validates the ecosystem agent contract: `agent.yaml` at the repo root, and
that the commands it names actually resolve.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AGENT_YAML = REPO_ROOT / "agent.yaml"

REQUIRED_KEYS = {
    "name",
    "role",
    "default_sensitivity_tier",
    "entrypoint",
    "health_check_command",
    "vault_write_path",
    "sandboxed",
}


def _load() -> dict:
    return yaml.safe_load(AGENT_YAML.read_text(encoding="utf-8"))


def test_agent_yaml_exists_at_repo_root():
    assert AGENT_YAML.is_file()


def test_agent_yaml_has_required_keys():
    data = _load()
    assert REQUIRED_KEYS <= set(data)


def test_agent_yaml_identity():
    data = _load()
    assert data["name"] == "Alfred"
    assert data["default_sensitivity_tier"] == "personal-token"
    assert data["sandboxed"] is False
    assert data["vault_write_path"] == "agents/Alfred/"


def test_agent_yaml_commands_reference_the_renamed_package():
    data = _load()
    assert "alfred" in data["entrypoint"]
    assert "alfred" in data["health_check_command"]
    assert "--health" in data["health_check_command"]
