"""Vault integration: read-before-explain and write-progress, both gated on
VAULT_PATH. The single most important behavior is the no-op path — with
VAULT_PATH unset, Alfred must do zero filesystem access and work exactly as
before.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from alfred import vault
from alfred.config import Settings


def _settings(tmp_path: Path | None = None) -> Settings:
    return Settings(vault_path=str(tmp_path) if tmp_path else None, _env_file=None)


# --- no-op when unconfigured --------------------------------------------------


def test_find_relevant_notes_is_a_noop_when_vault_path_unset():
    s = _settings(None)
    assert vault.find_relevant_notes(s, "sliding window") == []


def test_write_progress_note_is_a_noop_when_vault_path_unset():
    s = _settings(None)
    result = vault.write_progress_note(
        s,
        user_handle="dev",
        archetype="sliding_window",
        streak_days=3,
        mastery=1.0,
        next_due=date(2026, 1, 1),
    )
    assert result is None


def test_is_configured_reflects_vault_path(tmp_path):
    assert vault.is_configured(_settings(None)) is False
    assert vault.is_configured(_settings(tmp_path)) is True


# --- read: find_relevant_notes ------------------------------------------------


def test_find_relevant_notes_matches_on_filename_or_content(tmp_path):
    friday_dir = tmp_path / vault.READ_SUBDIR
    friday_dir.mkdir(parents=True)
    (friday_dir / "sliding-window.md").write_text(
        "# Sliding window\nTwo pointers that grow and shrink a range.", encoding="utf-8"
    )
    (friday_dir / "unrelated.md").write_text("# Something else entirely", encoding="utf-8")

    s = _settings(tmp_path)
    matches = vault.find_relevant_notes(s, "Longest Substring (sliding window pattern)")

    assert len(matches) == 1
    assert matches[0].path.name == "sliding-window.md"
    assert "growing" not in matches[0].content  # sanity: real content, not a stub
    assert "Two pointers" in matches[0].content


def test_find_relevant_notes_returns_empty_when_read_dir_missing(tmp_path):
    # VAULT_PATH exists but has no Friday/ subdirectory yet.
    s = _settings(tmp_path)
    assert vault.find_relevant_notes(s, "sliding window") == []


def test_notes_as_context_renders_and_truncates(tmp_path):
    friday_dir = tmp_path / vault.READ_SUBDIR
    friday_dir.mkdir(parents=True)
    (friday_dir / "note.md").write_text("body text", encoding="utf-8")
    s = _settings(tmp_path)

    notes = vault.find_relevant_notes(s, "note")
    context = vault.notes_as_context(notes)
    assert "body text" in context
    assert vault.notes_as_context([]) == ""


# --- write: write_progress_note -----------------------------------------------


def test_write_progress_note_writes_markdown_with_frontmatter(tmp_path):
    s = _settings(tmp_path)
    path = vault.write_progress_note(
        s,
        user_handle="dev",
        archetype="sliding_window",
        streak_days=5,
        mastery=0.8,
        next_due=date(2026, 9, 14),
    )

    assert path is not None
    assert path.parent == tmp_path / vault.WRITE_SUBDIR
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "agent: Alfred" in text
    assert "pattern_archetype: sliding_window" in text
    assert "streak_days: 5" in text
    assert "next_due: 2026-09-14" in text


def test_write_progress_note_overwrites_the_same_user_archetype_pair(tmp_path):
    s = _settings(tmp_path)
    first = vault.write_progress_note(
        s, user_handle="dev", archetype="graphs", streak_days=1, mastery=0.5, next_due=date(2026, 1, 1)
    )
    second = vault.write_progress_note(
        s, user_handle="dev", archetype="graphs", streak_days=2, mastery=0.9, next_due=date(2026, 1, 5)
    )
    assert first == second
    assert "streak_days: 2" in second.read_text(encoding="utf-8")
