"""Backend selection and the local (Ollama) path of the Mentor. No real model is
contacted: reachability and the completion call are monkeypatched."""

from types import SimpleNamespace

from alfred.config import Settings
from alfred.mentor import llm
from alfred.mentor.llm import Mentor

CARD = SimpleNamespace(title="Two Sum", slug="two-sum", patterns=[SimpleNamespace(name="hash_map")])


def _settings(**kw):
    base = dict(jwt_secret="x" * 32, llm_backend="auto", anthropic_api_key=None, vault_path=None)
    base.update(kw)
    return Settings(**base)


def test_off_backend_is_unavailable(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: True)
    m = Mentor(_settings(llm_backend="off"))
    assert m.backend == "off" and not m.available
    assert m.explain("hash maps") is None


def test_auto_prefers_local_ollama(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: True)
    assert Mentor(_settings(anthropic_api_key="sk-test")).backend == "ollama"


def test_auto_offline_when_nothing_available(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: False)
    assert Mentor(_settings()).backend == "off"


def test_ollama_forced_but_unreachable_stays_offline(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: False)
    assert Mentor(_settings(llm_backend="ollama", anthropic_api_key="sk-test")).backend == "off"


def test_local_nudge_passes_gate(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: True)
    m = Mentor(_settings())
    monkeypatch.setattr(m, "_complete_json", lambda *a, **k: {"nudge": "What could you remember about numbers you've already seen?"})
    hint = m.socratic_followup(CARD, "for i in x: pass", "nested loop", 2)
    assert hint is not None and hint.source == "llm"


def test_local_nudge_with_code_is_rejected_by_gate(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: True)
    m = Mentor(_settings())
    monkeypatch.setattr(m, "_complete_json", lambda *a, **k: {"nudge": "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        return [seen[target - n], i]"})
    assert m.socratic_followup(CARD, "", "", 2) is None


def test_explain_builds_on_real_notes_and_drops_invented_citations(monkeypatch, tmp_path):
    notes = tmp_path / "04-dsa"
    notes.mkdir()
    (notes / "hash-map-basics.md").write_text("# Hash map basics\nO(1) average lookup via hashing.", encoding="utf-8")
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: True)
    m = Mentor(_settings(vault_path=str(tmp_path)))
    seen = {}

    def fake(system, user, schema, max_tokens=300):
        seen["user"] = user
        return {"explanation": "A hash map maps keys to buckets.", "builds_on": ["hash map basics", "made up note"], "check_question": "Why is worst case O(n)?"}

    monkeypatch.setattr(m, "_complete_json", fake)
    r = m.explain("hash map")
    assert "O(1) average lookup" in seen["user"]
    assert r["builds_on"] == ["hash map basics"]
    assert r["notes_used"] == ["hash map basics"] and r["backend"] == "ollama"


def test_explain_ignores_other_agents_output(monkeypatch, tmp_path):
    (tmp_path / "agents" / "Alfred").mkdir(parents=True)
    (tmp_path / "agents" / "Alfred" / "hash-map-progress.md").write_text("hash map streak 3", encoding="utf-8")
    monkeypatch.setattr(llm, "_ollama_reachable", lambda host: True)
    m = Mentor(_settings(vault_path=str(tmp_path)))
    monkeypatch.setattr(m, "_complete_json", lambda *a, **k: {"explanation": "x", "check_question": "y"})
    assert m.explain("hash map")["notes_used"] == []


def test_ollama_ctx_grows_only_when_prompt_needs_it():
    from alfred.mentor.llm import _ollama_ctx
    assert _ollama_ctx(2000, 600) == {}
    assert _ollama_ctx(14000, 600) == {"num_ctx": 8192}
    assert _ollama_ctx(10**7, 600) == {"num_ctx": 32768}
