"""Vault read-before-explain, at the point it actually matters: the LLM
personalized nudge in mentor/llm.py. With VAULT_PATH unset this must not touch
the filesystem or change the prompt sent to the model; with it set and a
matching note present, the note's content must be folded into the prompt.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from alfred.config import Settings
from alfred.mentor.cards import PatternGuess, ProblemCard, HintLadder
from alfred.mentor.llm import Mentor


def _card() -> ProblemCard:
    return ProblemCard(
        slug="two-sum",
        title="Two Sum",
        difficulty="Easy",
        patterns=[PatternGuess(name="hash_map", confidence=0.9)],
        hint_ladder=HintLadder(l1="a", l2="b", l3="c", l4="d"),
    )


class _FakeContentBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _RecordingMessages:
    """Stands in for `anthropic.Anthropic().messages`, capturing the prompt it
    was called with so the test can assert on it, and returning a canned
    (schema-valid) nudge.
    """

    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        payload = json.dumps({"nudge": "Have you considered a hash map?"})
        return SimpleNamespace(content=[_FakeContentBlock(payload)])


def _mentor_with_fake_client(vault_path: str | None) -> tuple[Mentor, _RecordingMessages]:
    settings = Settings(anthropic_api_key=None, vault_path=vault_path, _env_file=None)
    mentor = Mentor(settings)
    fake_messages = _RecordingMessages()
    mentor._client = SimpleNamespace(messages=fake_messages)  # bypass the real anthropic client
    return mentor, fake_messages


def test_no_vault_configured_sends_no_notes_context(monkeypatch):
    mentor, fake = _mentor_with_fake_client(vault_path=None)
    result = mentor.socratic_followup(_card(), "code", "no issues found", level=1)

    assert result is not None
    assert "already has their own notes" not in fake.last_kwargs["messages"][0]["content"]


def test_matching_vault_note_is_folded_into_the_prompt(tmp_path):
    friday_dir = tmp_path / "Friday"
    friday_dir.mkdir()
    (friday_dir / "hash-map.md").write_text(
        "# Hash map\nO(1) average lookup by trading space for time.", encoding="utf-8"
    )

    mentor, fake = _mentor_with_fake_client(vault_path=str(tmp_path))
    result = mentor.socratic_followup(_card(), "code", "no issues found", level=1)

    assert result is not None
    prompt = fake.last_kwargs["messages"][0]["content"]
    assert "already has their own notes" in prompt
    assert "O(1) average lookup" in prompt


def test_no_matching_vault_note_leaves_prompt_unchanged(tmp_path):
    friday_dir = tmp_path / "Friday"
    friday_dir.mkdir()
    (friday_dir / "unrelated.md").write_text("# Something else", encoding="utf-8")

    mentor, fake = _mentor_with_fake_client(vault_path=str(tmp_path))
    mentor.socratic_followup(_card(), "code", "no issues found", level=1)

    prompt = fake.last_kwargs["messages"][0]["content"]
    assert "already has their own notes" not in prompt
