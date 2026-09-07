"""The MCP server (alfred/mcp_server.py) — registration and one real
end-to-end pass through each tool, against a temporary on-disk SQLite DB so
these tests never touch the developer's real database.

Tools are exercised through `server.call_tool`, the same path a real MCP
client (Claude Desktop/Code, or an orchestrator agent) would use — not by
calling the underlying Python functions directly — so a change to how the
tool is wired to MCP (a renamed parameter, a broken decorator) shows up here.
"""

from __future__ import annotations

import asyncio

import pytest


@pytest.fixture
def mcp_db(tmp_path, monkeypatch):
    """Point Alfred at a fresh on-disk sqlite file for the duration of the
    test. `mcp_server._db_session` reads `get_settings().database_url` fresh
    on every call (see its docstring) rather than the `alfred.db` module's
    import-time engine, so clearing the lru_cache is enough — no module
    reload needed, which would otherwise leak a stale engine into every other
    test module that imports `alfred.db` in this same process.
    """
    db_path = tmp_path / "mcp_test.db"
    monkeypatch.setenv("ALFRED_DATABASE_URL", f"sqlite:///{db_path}")

    import alfred.config as config_mod

    config_mod.get_settings.cache_clear()

    import alfred.mcp_server as mcp_server_mod

    yield mcp_server_mod

    config_mod.get_settings.cache_clear()


def _call(server, name, args):
    result = asyncio.run(server.call_tool(name, args))
    assert result.is_error is False, result
    return result.content[0].text


def test_all_four_tools_are_registered(mcp_db):
    tools = asyncio.run(mcp_db.server.list_tools())
    names = {t.name for t in tools}
    assert names == {"get_hint", "submit_for_ac_gate", "get_review", "get_interview_questions"}


def test_get_hint_returns_a_code_free_ladder_nudge(mcp_db):
    text = _call(mcp_db.server, "get_hint", {"slug": "two-sum", "level": 1})
    assert "level 1" in text
    assert "Hints remaining today" in text


def test_full_solution_is_refused_before_the_gate_opens(mcp_db):
    text = _call(mcp_db.server, "get_hint", {"slug": "two-sum", "level": 5})
    assert "Gate refused" in text


def test_submit_for_ac_gate_then_review_and_interview_unlock(mcp_db):
    server = mcp_db.server
    code = (
        "def twoSum(nums, target):\n"
        "    seen = {}\n"
        "    for i, n in enumerate(nums):\n"
        "        if target - n in seen:\n"
        "            return [seen[target - n], i]\n"
        "        seen[n] = i\n"
    )

    # Before the gate opens, both post-AC tools refuse.
    assert "Gate refused" in _call(server, "get_review", {"slug": "two-sum", "code": code})
    assert "Gate refused" in _call(server, "get_interview_questions", {"slug": "two-sum", "code": code})

    gate = _call(server, "submit_for_ac_gate", {"slug": "two-sum", "verdict": "Accepted"})
    assert "Accepted" in gate
    assert "Gate open" in gate

    review = _call(server, "get_review", {"slug": "two-sum", "code": code})
    assert "Verdict:" in review

    interview = _call(server, "get_interview_questions", {"slug": "two-sum", "code": code})
    assert interview  # at least one question, non-empty


def test_submit_for_ac_gate_rejects_a_non_accepted_verdict(mcp_db):
    text = _call(mcp_db.server, "submit_for_ac_gate", {"slug": "two-sum", "verdict": "Wrong Answer"})
    assert "gate stays closed" in text
