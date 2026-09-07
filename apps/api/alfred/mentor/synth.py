"""Build a teachable Problem Card for a problem nobody has authored one for.

This is what closes the coverage hole. `CardStore` holds a few dozen curated
cards; a learner opening any other problem used to get a 404 and a dead panel.
Here, the archetype inferred in `infer.py` is rendered through the ordinary
`card_builder`, so a synthesized card is the same validated `ProblemCard` as a
hand-written one and passes through the same AC-gate checks — a generated ladder
that somehow acquired code fails to build rather than reaching a learner.

Three honesty rules shape everything below, because the failure mode here is not
"no card" but "a confident card about the wrong pattern":

  * `verified` is always False. The panel badges it and offers a report link.
  * Below the inference confidence floor we serve `general-reasoning` — the
    pattern-free method — rather than the best-scoring guess. Being told "I
    don't recognise this one, let's reason it out" is useful; being taught
    sliding-window on a problem that isn't one is worse than silence.
  * No approach carries code. Hand-written cards ship per-problem solutions; we
    cannot generate one that is correct, and a plausible-looking wrong solution
    handed over post-AC is the most damaging thing this file could do. The named
    trade-off and its complexity are still worth having without it.
"""

from __future__ import annotations

from ..analysis import CodeSignals
from . import archetypes
from .card_builder import Spec, build
from .cards import ProblemCard
from .infer import Inference, infer

FALLBACK_ARCHETYPE = "general-reasoning"


def _understanding(title: str, statement: str | None, inference: Inference) -> str:
    """The plain-language restatement shown pre-AC.

    Deliberately not a summary of the problem: we would be paraphrasing a
    statement the learner is already looking at, and a bad paraphrase of a
    problem is worse than none. Instead it says what kind of problem this looks
    like and how sure we are — which is information they do not already have,
    and is the honest framing for a card nobody checked.
    """
    if not inference.confident:
        return (
            f"I don't have a hand-written card for {title}, and its tags don't point "
            "clearly at one pattern I know — so rather than guess, the hints below "
            "work from the problem itself: restate it, find what determines the "
            "answer, then find the work you're repeating. That's the method that "
            "works when you don't recognise a problem, which is most of them."
        )

    arch = archetypes.get(inference.archetype)
    why = f" ({inference.evidence[0]})" if inference.evidence else ""
    hedge = (
        " That's a reasonable read rather than a certain one, so if the hints "
        "start pulling away from the problem, trust the problem."
        if inference.confidence < 0.55
        else ""
    )
    return (
        f"There's no hand-written card for {title} yet, so this one is assembled "
        f"from the pattern it looks like: {arch.name.lower()}{why}. {arch.summary}"
        f"{hedge} Everything below is generated — if a hint doesn't fit the problem, "
        "the report link is what fixes it."
    )


def synthesize(
    slug: str,
    title: str | None = None,
    difficulty: str | None = None,
    topics=None,
    statement: str | None = None,
    signals: CodeSignals | None = None,
    inference: Inference | None = None,
) -> tuple[ProblemCard, Inference]:
    """Return a validated card for `slug`, plus the inference that produced it."""
    title = (title or slug.replace("-", " ").title()).strip()
    inference = inference or infer(title, topics, statement, signals)

    key = inference.archetype if inference.confident else FALLBACK_ARCHETYPE
    arch = archetypes.get(key)

    # The archetype's own topics describe the pattern; the problem's tags
    # describe the problem. Both are useful and they are not the same list, so
    # the page's tags lead and the archetype's fill in when there are none.
    tags = [t.strip().lower() for t in (topics or []) if t and t.strip()]

    # Only the inferred pattern is surfaced, never the runner-up. A second
    # pattern shown at a made-up 0.3 reliably turned out to be noise rather than
    # a real second opinion — Add Two Numbers drew Backtracking off its
    # "recursion" tag, then Bit Manipulation off "math" — and printing a wrong
    # pattern next to a right one costs more than the hedge is worth. The
    # confidence on the single guess already carries the uncertainty, and a
    # genuine tie falls below the floor and gets the pattern-free ladder anyway.
    spec = Spec(
        slug=slug,
        title=title,
        difficulty=(difficulty or "Unknown").capitalize(),
        archetype=key,
        subs=inference.nouns,
        understanding=_understanding(title, statement, inference),
        topics=tuple(tags) or arch.topics,
        # No `code`: see the module docstring. Approaches keep their idea and
        # complexity, which is the part an archetype can honestly supply.
        code={},
        verified=False,
    )

    card = build(spec)
    # Overwrite the builder's fixed 0.85 with what we actually believe.
    for pattern in card.patterns[:1]:
        pattern.confidence = round(inference.confidence, 2) if inference.confident else 0.25
    card.generated_by = (
        f"inferred:{key}@{inference.confidence:.2f}"
        if inference.confident
        else f"fallback:{key}(best={inference.archetype}@{inference.confidence:.2f})"
    )
    return card, inference
