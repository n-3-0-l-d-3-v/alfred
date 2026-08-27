"""HintService — the serving layer of the AC gate, plus the offline review.

Serving rules:
  * pre-AC (session.solved is False): only ladder levels 1-4, all code-free.
    Level 5+ (full solution) is refused.
  * post-AC: level 5+ returns approaches with code; the post-AC payload opens.

Cost rules (the free-tier fence):
  * ladder hints are card reads -> source="card", capped by `card_hints_per_day`.
  * personalized nudges are Haiku calls -> source="llm", capped by `llm_calls_per_day`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session as DbSession

from ..analysis import CodeSignals, analyze
from .. import problem_meta
from ..gamification import budget
from ..models import HintEvent, Session, User
from . import personalize, probes
from .cards import CardStore, ProblemCard
from .contracts import ApproachOut, PostACPayload, PreACHint, RichReview
from .llm import Mentor
from .review import build_review


class HintGateError(Exception):
    """Raised when a learner requests something the AC gate forbids (pre-AC)."""


class BudgetError(Exception):
    """Raised when a daily cap is hit."""


class CardMissingError(Exception):
    """No Problem Card exists for this slug and none could be generated.

    Retained for the endpoint layer, but no longer reachable in normal use:
    `_require_card` generates a card from the problem's archetype when none was
    authored. It survives as the honest failure for a card that cannot even be
    built — a corrupt archetype library, say — rather than being deleted and
    turning that into an opaque 500.
    """


# Levels 1-4 are the code-free ladder. 5 == full solution (post-AC only).
FULL_SOLUTION_LEVEL = 5


class HintService:
    def __init__(self, cards: CardStore, mentor: Mentor):
        self._cards = cards
        self._mentor = mentor

    def _require_card(self, db: DbSession, session: Session) -> ProblemCard:
        """The card for this session's problem, generating one if need be.

        Every feature routes through here, so generation happening at this level
        rather than at session start is what makes the whole surface — hints,
        review, interview, the post-AC payload — work on an unauthored problem
        instead of just the first of them.
        """
        card = self._cards.get(session.slug)
        if card is not None:
            return card
        try:
            meta = problem_meta.lookup(db, session.platform, session.slug)
            return self._cards.get_or_synthesize(session.slug, **problem_meta.as_kwargs(meta))
        except Exception as exc:  # pragma: no cover — archetype library is tested
            raise CardMissingError(session.slug) from exc

    # --- hints ---------------------------------------------------------------

    def get_hint(
        self,
        db: DbSession,
        user: User,
        session: Session,
        level: int,
        code: str | None = None,
        personalized: bool = False,
    ) -> PreACHint:
        card = self._require_card(db, session)

        # --- the gate ---
        if level >= FULL_SOLUTION_LEVEL and not session.solved:
            raise HintGateError(
                "The full solution unlocks after you get a passing submission. "
                "Solve it yourself first — that's the whole point. Try a lower hint level."
            )
        if level < 1 or level > 4:
            raise HintGateError("pre-AC hints are levels 1-4")

        # --- personalized (paid) path: still code-free ---
        if personalized and code and self._mentor.available:
            if budget.remaining(db, user.id, "llm", self._settings_llm_cap()):
                signals = analyze(session.language, code)
                nudge = self._mentor.socratic_followup(
                    card, code, self._summarize(signals), level
                )
                if nudge is not None:
                    self._record(db, user, session, level, source="llm", cost=1)
                    nudge.hints_remaining_today = budget.remaining(
                        db, user.id, "llm", self._settings_llm_cap()
                    )
                    return nudge
            # fall through to the free card path if capped or the call failed

        # --- free card path, personalized against their actual code ---
        cap = self._settings_card_cap()
        if not budget.remaining(db, user.id, "card", cap):
            raise BudgetError(
                f"You've used all {cap} hint reads today. They refresh tomorrow — "
                "or solve a problem clean to earn breathing room."
            )

        # The card supplies the teaching; the learner's code decides which rung
        # they get and how it opens. Without this the ladder reads like a
        # printed solutions manual — the same four sentences for everyone, in
        # the same order, regardless of what is on screen.
        signals = analyze(session.language, code) if code else None
        served_level, note = (
            personalize.suggest_level(signals, level, session.hints_used)
            if signals
            else (level, None)
        )
        rung = card.hint_ladder.level(served_level)
        # `hints_used` walks the observation list down a rung each time, so the
        # ladder does not open every step with the same sentence about their code.
        nudge = (
            personalize.compose(rung, signals, note, seen=session.hints_used)
            if signals
            else rung
        )
        if signals and not signals.parsed:
            # A broken parse has two very different causes. If the code itself
            # is malformed, say so and point at it — a learner staring at a
            # syntax error does not need a Socratic question about hash maps.
            # If we simply couldn't read the language, that's our problem, not
            # theirs, and the hint should admit it rather than pretend.
            syntax = personalize.syntax_help(signals)
            nudge = f"{syntax} {rung}" if syntax else f"{personalize.unparsed_note(signals)} {rung}"

        self._record(db, user, session, served_level, source="card", cost=0)
        return PreACHint(
            level=served_level,
            kind="ladder",
            nudge=nudge,
            source="card",
            hints_remaining_today=budget.remaining(db, user.id, "card", cap),
        )

    # --- post-AC payload -----------------------------------------------------

    def post_ac_payload(self, db: DbSession, session: Session) -> PostACPayload:
        if not session.solved:
            raise HintGateError("Post-AC content unlocks after a passing submission.")
        card = self._require_card(db, session)
        return PostACPayload(
            slug=card.slug,
            approaches=[ApproachOut(**a.model_dump()) for a in card.approaches],
            pitfalls=card.pitfalls,
            edge_cases=card.edge_cases,
            rewrite_challenges=card.rewrite_challenges,
            complexity=card.complexity,
        )

    # --- review (offline, unlimited; LLM enriches later) ---------------------

    def review(
        self,
        db: DbSession,
        session: Session,
        code: str,
        persona: str = "mentor",
        failed_attempts: int = 0,
    ) -> RichReview:
        """Multi-lens review. Free and unlimited — it never calls the model."""
        if not session.solved:
            raise HintGateError("Reviews unlock after a passing submission.")
        card = self._require_card(db, session)
        signals = analyze(session.language, code)
        return build_review(
            card,
            signals,
            persona_key=persona,
            hints_used=session.hints_used,
            failed_attempts=failed_attempts,
        )

    # --- interview -----------------------------------------------------------

    def interview(self, db: DbSession, session: Session, code: str, limit: int = 4) -> list[dict]:
        """Questions about this submission, without their answers.

        Answers are withheld until the learner commits to their own — see
        `interview_answers`. Handing both over at once turns the exercise into
        reading comprehension, which is not what it is for.
        """
        if not session.solved:
            raise HintGateError(
                "Interview mode opens after you pass. Defending a solution you "
                "haven't got yet is just a harder way to ask for a hint."
            )
        card = self._require_card(db, session)
        signals = analyze(session.language, code)
        return [
            {"key": p.key, "question": p.question}
            for p in probes.generate(card, signals, limit=limit)
        ]

    def interview_answers(self, db: DbSession, session: Session, code: str, limit: int = 4) -> list[dict]:
        """The model answers, revealed after the learner has committed to theirs."""
        if not session.solved:
            raise HintGateError("Interview mode opens after a passing submission.")
        card = self._require_card(db, session)
        signals = analyze(session.language, code)
        return [
            {
                "key": p.key,
                "question": p.question,
                "model_answer": p.model_answer,
                "why_asked": p.why_asked,
            }
            for p in probes.generate(card, signals, limit=limit)
        ]

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _summarize(signals: CodeSignals) -> str:
        return (
            f"loops={signals.loops}, depth={signals.max_loop_depth}, "
            f"recursion={signals.has_recursion}, memo={signals.has_memoization}, "
            f"ds={signals.data_structures}, est={signals.estimated_time_complexity()}"
        )

    def _record(self, db: DbSession, user: User, session: Session, level: int, source: str, cost: int) -> None:
        db.add(HintEvent(user_id=user.id, session_id=session.id, level=level, source=source, cost=cost))
        session.hints_used += 1
        db.commit()

    # cap accessors read from settings lazily so tests can override cheaply
    def _settings_card_cap(self) -> int:
        from ..config import get_settings

        return get_settings().card_hints_per_day

    def _settings_llm_cap(self) -> int:
        from ..config import get_settings

        return get_settings().llm_calls_per_day
