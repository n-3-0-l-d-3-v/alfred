"""Model wrapper with a pluggable backend. Degrades gracefully: with no backend
every method returns None and callers fall back to the offline card/heuristic
path. This is what lets the whole app run and be tested without credentials.

Backends (settings.llm_backend):
  auto      -> local Ollama if reachable, else Anthropic if a key is set, else offline
  ollama    -> local only: free, private, nothing leaves the machine
  anthropic -> paid API (the original path)
  off       -> offline only

The one hard invariant: the pre-AC path uses a system prompt and a structured
output schema that cannot carry code, and the result is re-validated through
`PreACHint` before it ever leaves this module — whichever backend produced it.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from .. import vault
from ..config import Settings
from .cards import ProblemCard
from .contracts import PreACHint, looks_like_code

log = logging.getLogger("alfred.mentor.llm")

_PRE_AC_SYSTEM = (
    "You are a Socratic coding mentor. The learner has NOT solved the problem yet. "
    "You must NEVER provide code, pseudocode, or a step-by-step algorithm that could be "
    "transcribed into a solution. Ask one guiding question or point at one concept that "
    "moves them forward by the smallest useful step. Output only a short 'nudge'."
)

# JSON schema with no field that can hold code — structural half of the AC gate.
_PRE_AC_SCHEMA = {
    "type": "object",
    "properties": {"nudge": {"type": "string"}},
    "required": ["nudge"],
    "additionalProperties": False,
}

_EXPLAIN_SYSTEM = (
    "You are a computer-science tutor. Explain the concept clearly and correctly for a CS student. "
    "If the learner's own notes are provided, BUILD ON THEM: reference them by title, do not repeat "
    "what they already wrote, and fill the gaps they missed. Never invent facts about the learner. "
    "Put the WHOLE explanation (including any steps) inside the explanation field and finish every "
    "sentence; 120-300 words, plain language, one small example if it helps. "
    "End with exactly one question that checks understanding."
)

_EXPLAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},
        "builds_on": {"type": "array", "items": {"type": "string"}},
        "check_question": {"type": "string"},
    },
    "required": ["explanation", "check_question"],
    "additionalProperties": False,
}


def _ollama_reachable(host: str) -> bool:
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


class Mentor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        self.backend = "off"
        choice = (settings.llm_backend or "auto").lower()

        if choice in ("auto", "ollama") and _ollama_reachable(settings.ollama_host):
            self.backend = "ollama"
        elif choice in ("auto", "anthropic") and settings.anthropic_api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                self.backend = "anthropic"
            except Exception as exc:  # pragma: no cover - depends on env
                log.warning("anthropic client unavailable, running offline: %s", exc)

    @property
    def available(self) -> bool:
        return self.backend != "off"

    # -- backend plumbing -------------------------------------------------

    def _complete_json(self, system: str, user: str, schema: dict, max_tokens: int = 300) -> dict | None:
        """One structured completion from whichever backend is active. None on any failure."""
        try:
            if self.backend == "ollama":
                body = json.dumps({
                    "model": self._settings.ollama_model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "format": schema,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": max_tokens * 2},
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{self._settings.ollama_host}/api/chat", data=body,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=180) as r:
                    text = json.loads(r.read())["message"]["content"]
            elif self.backend == "anthropic":
                resp = self._client.messages.create(  # type: ignore[union-attr]
                    model=self._settings.haiku_model,
                    max_tokens=max_tokens,
                    system=system,
                    output_config={"format": {"type": "json_schema", "schema": schema}},
                    messages=[{"role": "user", "content": user}],
                )
                text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
            else:
                return None
            return json.loads(text)
        except Exception as exc:  # pragma: no cover - network/model dependent
            log.warning("%s completion failed: %s", self.backend, exc)
            return None

    # -- capabilities -----------------------------------------------------

    def socratic_followup(
        self, card: ProblemCard, code: str, signals_summary: str, level: int
    ) -> PreACHint | None:
        """A personalized, still-code-free nudge based on the learner's own code.

        One model call. Returns None (caller falls back to the card) on any
        failure. The response is forced back through `PreACHint`, so even a
        misbehaving model cannot smuggle code past the gate.
        """
        if not self.available:
            return None

        # Vault read-before-explain: if the learner already has notes on this
        # problem's pattern (VAULT_PATH configured, see ../vault.py), point the
        # model at them instead of having it re-explain the concept from
        # scratch. A no-op — zero filesystem access — when VAULT_PATH is unset.
        concept = " ".join([card.title, *(p.name for p in card.patterns)])
        notes_context = vault.notes_as_context(vault.find_relevant_notes(self._settings, concept))

        user = (
            f"Problem: {card.title} ({card.slug}). "
            f"The learner is stuck at hint level {level}. "
            f"Static analysis of their current code: {signals_summary}. "
            f"Their code:\n{code[:2000]}\n\n"
            + (
                f"The learner already has their own notes on related concepts — "
                f"reference these instead of re-explaining them from scratch:\n{notes_context}\n\n"
                if notes_context
                else ""
            )
            + "Give exactly one Socratic nudge that addresses what they seem to be missing. No code."
        )
        data = self._complete_json(_PRE_AC_SYSTEM, user, _PRE_AC_SCHEMA)
        nudge = (data or {}).get("nudge", "").strip()
        if not nudge:
            return None
        try:
            # Re-validate through the gate — raises if the model returned code.
            return PreACHint(level=level, kind="socratic", nudge=nudge, source="llm")
        except ValueError as exc:
            log.warning("model nudge rejected by the AC gate: %s", exc)
            return None

    def explain(self, concept: str) -> dict | None:
        """Explain a CS concept, building on the learner's own vault notes.

        Returns {explanation, builds_on, check_question, notes_used, backend}
        or None if no backend is available / the call fails. Concept
        explanations are not problem solutions, so there is no AC gate here,
        but code blocks are still stripped to keep it conceptual.
        """
        if not self.available or not concept.strip():
            return None
        notes = vault.find_relevant_notes(self._settings, concept, limit=4)
        context = vault.notes_as_context(notes, max_chars=3000)
        user = (
            f"Concept: {concept}\n\n"
            + (f"The learner's own notes (titles as headings):\n{context}\n" if context else "The learner has no notes on this yet.\n")
        )
        data = self._complete_json(_EXPLAIN_SYSTEM, user, _EXPLAIN_SCHEMA, max_tokens=700)
        if not data or not str(data.get("explanation", "")).strip():
            return None
        titles = {n.title for n in notes}
        question = str(data.get("check_question", "")).strip()
        explanation = data["explanation"].strip()
        if question and explanation.endswith(question):
            explanation = explanation[: -len(question)].rstrip()
        # drop dangling markdown headings the model sometimes leaves at the end
        lines = explanation.splitlines()
        while lines and (not lines[-1].strip() or lines[-1].lstrip().startswith("#")):
            lines.pop()
        explanation = "\n".join(lines).strip()

        def _match(cited: str) -> str | None:
            c = str(cited).strip().strip("#").strip().lower().replace("-", " ").replace("_", " ")
            return next((t for t in titles if c and (c == t or c in t or t in c)), None)

        # only keep citations that resolve to notes we actually gave it
        builds_on = sorted({m for m in (_match(c) for c in data.get("builds_on", [])) if m})
        return {
            "explanation": explanation,
            "builds_on": builds_on,
            "check_question": question,
            "notes_used": sorted(titles),
            "backend": self.backend,
            "contains_code": looks_like_code(data["explanation"]),
        }
