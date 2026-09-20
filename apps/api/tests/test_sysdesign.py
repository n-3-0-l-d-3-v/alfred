import pytest

from alfred import sysdesign as sd

GOOD = ("We generate base62 codes from a distributed counter and store code to url in a key-value store like dynamo. "
        "Reads dominate so we put a redis cache and a cdn in front, and return a 302 redirect. We shard by code and add replicas "
        "behind a load balancer for horizontal scaling. Links use a ttl for expiry and we rate limit creation to stop spam abuse. "
        "Analytics are written asynchronously through a queue so redirects stay fast under heavy load, and every link record stores its creation time and owner.")


def test_all_scenarios_have_rubrics_and_ladders():
    for s in sd.SCENARIOS.values():
        assert len(s.rubric) >= 6 and s.clarify and s.estimate and s.components and s.pitfalls
        for lvl in range(5):
            assert sd.hint(s.id, lvl)


def test_hints_never_leak_reference():
    for s in sd.SCENARIOS.values():
        for lvl in range(5):
            assert s.reference not in sd.hint(s.id, lvl)


def test_gate_refuses_thin_design():
    with pytest.raises(sd.SysDesignError, match="locked"):
        sd.review("url-shortener", "use a database")


def test_review_scores_and_reveals_after_real_attempt():
    r = sd.review("url-shortener", GOOD)
    assert r["score"] == 1.0 and r["reference"] and not r["missing"]


def test_review_flags_missing_concepts():
    r = sd.review("url-shortener", " ".join(["We store urls in a database with a cache"] * 12))
    assert r["missing"] and "storage choice" in r["covered"]


def test_unknown_scenario_and_level():
    with pytest.raises(sd.SysDesignError):
        sd.hint("nope", 1)
    with pytest.raises(sd.SysDesignError):
        sd.hint("url-shortener", 9)


def test_mcp_tools_registered():
    import asyncio

    from alfred import mcp_server

    names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
    assert {"sd_list", "sd_hint", "sd_review"} <= names
