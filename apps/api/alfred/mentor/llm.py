"""Claude wrapper. Degrades gracefully: with no API key every method returns
None and callers fall back to the offline card/heuristic path. This is what
lets the whole app run and be tested without credentials.

The one hard invariant: the pre-AC path uses a system prompt and a structured
output schema that cannot carry code, and the result is re-validated through
`PreACHint` before it ever leaves this module.
"""

from __future__ import annotations

import logging

from .. import vault
from ..config import Settings
from .cards import ProblemCard
from .contracts import PreACHint

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


class Mentor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None
        if settings.anthropic_api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            except Exception as exc:  # pragma: no cover - depends on env
                log.warning("anthropic client unavailable, running offline: %s", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    def socratic_followup(
        self, card: ProblemCard, code: str, signals_summary: str, level: int
    ) -> PreACHint | None:
        """A personalized, still-code-free nudge based on the learner's own code.

        Costs one Haiku call. Returns None (caller falls back to the card) on any
        failure. The response is forced back through `PreACHint`, so even a
        misbehaving model cannot smuggle code past the gate.
        """
        if not self._client:
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
        try:
            resp = self._client.messages.create(
                model=self._settings.haiku_model,
                max_tokens=300,
                system=_PRE_AC_SYSTEM,
                output_config={"format": {"type": "json_schema", "schema": _PRE_AC_SCHEMA}},
                messages=[{"role": "user", "content": user}],
            )
            text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
            import json

            nudge = json.loads(text).get("nudge", "").strip()
            if not nudge:
                return None
            # Re-validate through the gate — raises if the model returned code.
            return PreACHint(level=level, kind="socratic", nudge=nudge, source="llm")
        except Exception as exc:  # pragma: no cover - network/model dependent
            log.warning("socratic_followup failed, falling back to card: %s", exc)
            return None
