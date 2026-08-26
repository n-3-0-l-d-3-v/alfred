"""Problem Cards — the pre-generated knowledge base that makes the product cheap.

A card is generated once (offline, via the Batch API in Phase 1) and validated,
then served at runtime as a plain read. The card's hint ladder (L1-L4) is
validated code-free *at load time*, so the AC gate holds even if a bad card
slips into the KB.

For the dev slice, cards live as JSON in `cards_data/`. In production they live
in the `problem_cards` table (PLAN.md §4).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, field_validator

from .contracts import looks_like_code

_CARDS_DIR = Path(__file__).resolve().parent.parent / "cards_data"


class PatternGuess(BaseModel):
    name: str
    confidence: float


class HintLadder(BaseModel):
    l1: str
    l2: str
    l3: str
    l4: str

    @field_validator("l1", "l2", "l3", "l4")
    @classmethod
    def _no_code(cls, v: str) -> str:
        # This is where "cards are code-free pre-AC" is enforced for the whole KB.
        if looks_like_code(v):
            raise ValueError("hint ladder L1-L4 must be code-free (pre-AC contract)")
        return v

    def level(self, n: int) -> str:
        return {1: self.l1, 2: self.l2, 3: self.l3, 4: self.l4}[n]


class Approach(BaseModel):
    name: str
    idea: str
    time: str
    space: str
    code: str | None = None  # code is allowed here — approaches are post-AC only


class ProblemCard(BaseModel):
    slug: str
    title: str
    difficulty: str
    topics: list[str] = []
    patterns: list[PatternGuess] = []
    understanding: str = ""       # plain-language restatement (safe pre-AC)
    hint_ladder: HintLadder
    approaches: list[Approach] = []
    complexity: dict = {}
    pitfalls: list[dict] = []
    # Concrete "what happens if you do it wrong" demonstrations, each with the
    # input that exposes the mistake and the wrong output it produces.
    failure_cases: list[dict] = []
    edge_cases: list[str] = []
    rewrite_challenges: list[str] = []

    # Provenance. Hand-checked cards are `verified`; auto-generated long-tail
    # cards are not, and the UI badges them + offers a "this was bad" report so
    # the review queue is driven by real usage rather than guesswork.
    verified: bool = False
    generated_by: str | None = None  # e.g. "claude-opus-4-8 batch 2026-07"


class CardStore:
    """Loads and holds Problem Cards. Fail-fast: an invalid card (e.g. code in
    the hint ladder) raises at startup rather than leaking at request time."""

    def __init__(self) -> None:
        self._cards: dict[str, ProblemCard] = {}
        # Tracked separately from `verified`: a hand-written card can also be
        # unverified, and only these are safe to discard and rebuild.
        self._synthesized: set[str] = set()

    def load_dir(self, directory: Path | None = None) -> "CardStore":
        """Load hand-written JSON cards, then the archetype-built ones.

        Both sources produce the same validated `ProblemCard`. JSON loads first
        so a hand-written card wins on slug collision: those are the ones that
        have been checked line by line, and a generalised archetype should never
        silently replace a specialist's version of a problem.
        """
        directory = directory or _CARDS_DIR
        for path in sorted(directory.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            card = ProblemCard.model_validate(raw)
            self._cards[card.slug] = card
        self.load_specs()
        return self

    def load_specs(self, specs=None) -> "CardStore":
        """Build cards from archetype specializations (see `cards_src`)."""
        # Imported here rather than at module scope: cards_src imports the card
        # builder, which imports this module.
        from ..cards_src import ALL
        from .card_builder import build_all

        for card in build_all(list(specs) if specs is not None else ALL):
            self._cards.setdefault(card.slug, card)
        return self

    def get(self, slug: str) -> ProblemCard | None:
        return self._cards.get(slug)

    def get_or_synthesize(
        self,
        slug: str,
        title: str | None = None,
        difficulty: str | None = None,
        topics=None,
        statement: str | None = None,
    ) -> ProblemCard:
        """A card for `slug`, generating one from its archetype if none exists.

        This is what makes the product work on a problem nobody authored. An
        authored card always wins — those have been checked line by line, and a
        generalisation should never displace a specialist's version.

        Synthesized cards are memoised under their slug, so the second learner to
        open a problem gets the same plain dictionary read as a curated one. The
        cache is keyed only by slug because the inputs behind it (a problem's
        tags and statement) do not change; the one thing that would justify
        rebuilding is a better archetype library, and that ships as a restart.
        """
        card = self._cards.get(slug)
        if card is not None:
            return card

        from .synth import synthesize

        card, _ = synthesize(slug, title, difficulty, topics, statement)
        self._cards[slug] = card
        self._synthesized.add(slug)
        return card

    def is_synthesized(self, slug: str) -> bool:
        return slug in self._synthesized

    def slugs(self) -> list[str]:
        return sorted(self._cards)

    def __len__(self) -> int:
        return len(self._cards)
