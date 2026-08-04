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
from ..gamification import budget
from ..models import HintEvent, Session, User
from .cards import CardStore, ProblemCard
from .contracts import ApproachOut, PostACPayload, PreACHint, RichReview
from .llm import Mentor
from .review import build_review


class HintGateError(Exception):
    """Raised when a learner requests something the AC gate forbids (pre-AC)."""


class BudgetError(Exception):
    """Raised when a daily cap is hit."""


class CardMissingError(Exception):
    """No Problem Card exists for this slug yet."""


# Levels 1-4 are the code-free ladder. 5 == full solution (post-AC only).
FULL_SOLUTION_LEVEL = 5


class HintService:
    def __init__(self, cards: CardStore, mentor: Mentor):
        self._cards = cards
        self._mentor = mentor

    def _require_card(self, slug: str) -> ProblemCard:
        card = self._cards.get(slug)
        if card is None:
            raise CardMissingError(slug)
        return card

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
        card = self._require_card(session.slug)

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

        # --- free card path ---
        cap = self._settings_card_cap()
        if not budget.remaining(db, user.id, "card", cap):
            raise BudgetError(
                f"You've used all {cap} hint reads today. They refresh tomorrow — "
                "or solve a problem clean to earn breathing room."
            )
        self._record(db, user, session, level, source="card", cost=0)
        return PreACHint(
            level=level,
            kind="ladder",
            nudge=card.hint_ladder.level(level),
            source="card",
            hints_remaining_today=budget.remaining(db, user.id, "card", cap),
        )

    # --- post-AC payload -----------------------------------------------------

    def post_ac_payload(self, session: Session) -> PostACPayload:
        if not session.solved:
            raise HintGateError("Post-AC content unlocks after a passing submission.")
        card = self._require_card(session.slug)
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
        session: Session,
        code: str,
        persona: str = "mentor",
        failed_attempts: int = 0,
    ) -> RichReview:
        """Multi-lens review. Free and unlimited — it never calls the model."""
        if not session.solved:
            raise HintGateError("Reviews unlock after a passing submission.")
        card = self._require_card(session.slug)
        signals = analyze(session.language, code)
        return build_review(
            card,
            signals,
            persona_key=persona,
            hints_used=session.hints_used,
            failed_attempts=failed_attempts,
        )

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
