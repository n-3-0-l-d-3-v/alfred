"""Optional integration with an external "vault" — a folder of Markdown notes
shared across this personal multi-agent ecosystem (e.g. a sibling "Friday"
agent's own notes).

Two directions, both gated on the ``VAULT_PATH`` env var (``config.vault_path``):

* **Read before explain** — `find_relevant_notes` looks under
  ``<VAULT_PATH>/Friday/`` for notes that already cover a concept, so a hint
  or review can point at what the learner already captured instead of
  re-explaining it from scratch.
* **Write progress** — `write_progress_note` records streaks,
  mastery-per-pattern-archetype, and spaced-repetition due dates as Markdown
  with frontmatter under ``<VAULT_PATH>/Alfred/``. This is *in addition to*
  the Postgres-backed progress tracking in `gamification/`, not a
  replacement for it.

With ``VAULT_PATH`` unset (the default), every function here does zero
filesystem I/O and returns an empty/None result — Alfred works completely
standalone with no vault configured.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import Settings

READ_SUBDIR = "Friday"
WRITE_SUBDIR = "Alfred"

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")


@dataclass(frozen=True)
class VaultNote:
    path: Path
    title: str
    content: str


def _vault_root(settings: Settings) -> Path | None:
    if not settings.vault_path:
        return None
    return Path(settings.vault_path)


def is_configured(settings: Settings) -> bool:
    return _vault_root(settings) is not None


def find_relevant_notes(settings: Settings, concept: str, *, limit: int = 3) -> list[VaultNote]:
    """Notes under ``<VAULT_PATH>/Friday/`` whose filename or content mentions
    a word from `concept`. Returns `[]` (no filesystem access at all) when
    ``VAULT_PATH`` is unset or the read directory doesn't exist.
    """
    root = _vault_root(settings)
    if root is None:
        return []
    read_dir = root / READ_SUBDIR
    if not read_dir.is_dir():
        return []

    # Normalize "_"/"-" to a space so "hash_map" (a pattern-archetype name) and
    # "hash-map"/"hash map" (however a note happens to be titled) compare equal.
    terms = {t.lower().replace("_", " ").replace("-", " ") for t in _WORD_RE.findall(concept)}
    if not terms:
        return []

    matches: list[VaultNote] = []
    for md_path in sorted(read_dir.rglob("*.md")):
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        haystack = f"{md_path.stem}\n{text}".lower().replace("_", " ").replace("-", " ")
        if any(term in haystack for term in terms):
            title = md_path.stem.replace("-", " ").replace("_", " ")
            matches.append(VaultNote(path=md_path, title=title, content=text))
            if len(matches) >= limit:
                break
    return matches


def notes_as_context(notes: list[VaultNote], *, max_chars: int = 1500) -> str:
    """Render matched notes into a short block suitable for folding into an
    LLM prompt. Empty string for an empty list.
    """
    if not notes:
        return ""
    blob = "\n\n".join(f"### {n.title}\n{n.content.strip()}" for n in notes)
    return blob[:max_chars]


def write_progress_note(
    settings: Settings,
    *,
    user_handle: str,
    archetype: str,
    streak_days: int,
    mastery: float,
    next_due: date,
) -> Path | None:
    """Write one Markdown-with-frontmatter progress note per (user, archetype)
    pair to ``<VAULT_PATH>/Alfred/``, overwriting the previous note for that
    pair. Returns the written path, or `None` (no filesystem access at all)
    when ``VAULT_PATH`` is unset.
    """
    root = _vault_root(settings)
    if root is None:
        return None
    write_dir = root / WRITE_SUBDIR
    write_dir.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^a-z0-9]+", "-", f"{user_handle}-{archetype}".lower()).strip("-") or "progress"
    path = write_dir / f"{slug}.md"

    frontmatter = "\n".join(
        [
            "---",
            "agent: Alfred",
            f"user: {user_handle}",
            f"pattern_archetype: {archetype}",
            f"streak_days: {streak_days}",
            f"mastery: {mastery:.2f}",
            f"next_due: {next_due.isoformat()}",
            f"updated: {date.today().isoformat()}",
            "---",
            "",
        ]
    )
    body = (
        f"# {archetype} progress for {user_handle}\n\n"
        f"- Streak: {streak_days} day(s)\n"
        f"- Mastery: {mastery:.0%}\n"
        f"- Next spaced-repetition review due: {next_due.isoformat()}\n"
    )
    path.write_text(frontmatter + "\n" + body, encoding="utf-8")
    return path
