"""Turn an archetype plus a small specialization into a validated Problem Card.

A specialization is deliberately tiny — the nouns the archetype's templates need,
a plain-language restatement, and the per-problem code for each approach. Anything
an archetype already knows is not repeated here, so a card is roughly twenty lines
rather than ninety, and a fix to a pattern's teaching propagates to every problem
using it.

Cards may override any generated field. That matters because archetypes are
generalisations and some problems genuinely differ — Trapping Rain Water's edge
cases are not the generic two-pointer ones. The override is the escape hatch that
keeps the generalisation honest instead of forcing every problem to pretend it fits.

Everything still goes through `ProblemCard`, so the AC-gate validator runs on
generated cards exactly as it does on hand-written JSON: a ladder that somehow
acquires code fails to load, whatever produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import archetypes
from . import archetype_library  # noqa: F401  — registers the archetypes on import
from .cards import Approach, HintLadder, PatternGuess, ProblemCard


@dataclass
class Spec:
    """The per-problem half of a card."""

    slug: str
    title: str
    difficulty: str
    archetype: str

    # Nouns filling the archetype's `{placeholders}`.
    subs: dict[str, str]

    # Plain-language restatement. Safe pre-AC: it describes the problem, not a
    # route through it. Written per problem because it is the one thing no
    # pattern can supply.
    understanding: str

    # Per-approach solution code, keyed by the archetype's approach name. Only
    # ever served post-AC. Approaches with no entry here are still listed with
    # their idea and complexity — a named trade-off is useful without code.
    code: dict[str, str] = field(default_factory=dict)

    topics: tuple[str, ...] = ()
    # Additional patterns to surface pre-AC alongside the archetype's own hint.
    extra_patterns: tuple[tuple[str, float], ...] = ()

    # Anything here replaces the generated value outright.
    overrides: dict = field(default_factory=dict)

    # Extra entries appended to the generated ones.
    extra_pitfalls: tuple[dict, ...] = ()
    extra_failure_cases: tuple[dict, ...] = ()
    extra_edge_cases: tuple[str, ...] = ()
    extra_rewrites: tuple[str, ...] = ()

    verified: bool = False


def build(spec: Spec) -> ProblemCard:
    """Render `spec` against its archetype into a validated ProblemCard."""
    arch = archetypes.get(spec.archetype)

    missing = arch.placeholders() - set(spec.subs)
    if missing:
        raise archetypes.MissingSubstitution(
            f"card '{spec.slug}' is missing substitutions for archetype "
            f"'{arch.key}': {sorted(missing)}"
        )

    ladder = HintLadder(**arch.ladder.render(spec.subs))

    approaches = [
        Approach(
            name=a.name,
            idea=archetypes.render_all((a.idea,), spec.subs)[0],
            time=a.time,
            space=a.space,
            code=spec.code.get(a.name),
        )
        for a in arch.approaches
    ]

    patterns = [PatternGuess(name=arch.pattern_hint or arch.name, confidence=0.85)]
    patterns += [PatternGuess(name=n, confidence=c) for n, c in spec.extra_patterns]

    card = ProblemCard(
        slug=spec.slug,
        title=spec.title,
        difficulty=spec.difficulty,
        topics=list(spec.topics or arch.topics),
        patterns=patterns,
        understanding=spec.understanding,
        hint_ladder=ladder,
        approaches=approaches,
        complexity={
            "target_time": arch.target_time,
            "target_space": arch.target_space,
            "brute_time": arch.brute_time,
        },
        pitfalls=archetypes.render_all(arch.pitfalls, spec.subs) + list(spec.extra_pitfalls),
        failure_cases=archetypes.render_all(arch.failure_cases, spec.subs)
        + list(spec.extra_failure_cases),
        edge_cases=archetypes.render_all(arch.edge_cases, spec.subs) + list(spec.extra_edge_cases),
        rewrite_challenges=archetypes.render_all(arch.rewrite_challenges, spec.subs)
        + list(spec.extra_rewrites),
        verified=spec.verified,
        generated_by=f"archetype:{arch.key}",
    )

    if spec.overrides:
        # Re-validate rather than mutating in place: an override that introduced
        # code into the ladder has to fail here, not at serve time.
        card = ProblemCard.model_validate({**card.model_dump(), **spec.overrides})
    return card


def build_all(specs: list[Spec]) -> list[ProblemCard]:
    """Build every spec, reporting all failures together.

    One card at a time would surface only the first problem in a batch, which
    makes authoring 150 of them needlessly serial.
    """
    cards, errors = [], []
    for spec in specs:
        try:
            cards.append(build(spec))
        except Exception as exc:
            errors.append(f"{spec.slug}: {type(exc).__name__}: {exc}")
    if errors:
        raise ValueError("card build failed:\n  " + "\n  ".join(errors))
    return cards
