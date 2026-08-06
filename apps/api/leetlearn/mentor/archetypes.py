"""Algorithmic archetypes — the reusable half of every Problem Card.

PLAN.md §6 budgets $166 of Batch API calls to generate a card per problem. That
buys 3,500 cards of unknown quality and no way to iterate cheaply on the prompt.
This module takes the other road: the *teaching* content for a problem is almost
entirely a property of its pattern, not of the problem. "You are rescanning data
you have already seen — what structure answers 'have I seen this?' in one step"
is the same insight for Two Sum, Contains Duplicate, and Group Anagrams.

So an archetype carries the pattern's whole teaching surface — a Socratic ladder,
the mistakes people actually make, concrete failure demonstrations, edge cases,
rewrite challenges — with `{placeholders}` for the nouns that differ per problem.
A card is then an archetype plus a small specialization. Card 400 costs about as
much effort as card 40, and nothing costs API credit.

The ladder templates are the sensitive part: they must survive
`looks_like_code`, because `HintLadder` refuses to load a card whose L1-L4 could
carry a solution. They are written as prose about *structure and intent*, never
as steps that transcribe into code. `test_archetypes.py` asserts this across the
whole library rather than trusting review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class MissingSubstitution(KeyError):
    """A card didn't supply a noun its archetype's templates require."""


@dataclass(frozen=True)
class LadderTemplate:
    """The four rungs, in increasing specificity. None of them may contain code.

    L1 reframes the problem so the learner notices what they're actually being
    asked. L2 names the quantity or relationship that matters. L3 points at the
    inefficiency without naming the fix. L4 describes the shape of the approach
    in prose — enough to unblock, not enough to paste.
    """

    l1: str
    l2: str
    l3: str
    l4: str

    def render(self, subs: dict[str, str]) -> dict[str, str]:
        return {name: _render(getattr(self, name), subs) for name in ("l1", "l2", "l3", "l4")}


@dataclass(frozen=True)
class ApproachTemplate:
    """An approach without code — the code is problem-specific and lives in the
    card's specialization, because it's the one part an archetype can't know."""

    name: str
    idea: str
    time: str
    space: str


@dataclass(frozen=True)
class Archetype:
    key: str
    name: str
    summary: str
    ladder: LadderTemplate

    target_time: str
    target_space: str
    brute_time: str

    approaches: tuple[ApproachTemplate, ...] = ()
    pitfalls: tuple[dict[str, str], ...] = ()
    failure_cases: tuple[dict[str, str], ...] = ()
    edge_cases: tuple[str, ...] = ()
    rewrite_challenges: tuple[str, ...] = ()

    # Pattern names surfaced pre-AC. Deliberately vaguer than the archetype key:
    # naming the exact technique to someone who hasn't solved it yet is most of
    # the answer, which is the thing the AC gate exists to prevent.
    pattern_hint: str = ""
    topics: tuple[str, ...] = field(default_factory=tuple)

    def placeholders(self) -> set[str]:
        """Every `{name}` any template in this archetype expects."""
        found: set[str] = set()
        for text in (self.ladder.l1, self.ladder.l2, self.ladder.l3, self.ladder.l4):
            found |= set(_PLACEHOLDER.findall(text))
        for group in (self.pitfalls, self.failure_cases):
            for entry in group:
                for value in entry.values():
                    found |= set(_PLACEHOLDER.findall(value))
        for text in self.edge_cases + self.rewrite_challenges:
            found |= set(_PLACEHOLDER.findall(text))
        for approach in self.approaches:
            found |= set(_PLACEHOLDER.findall(approach.idea))
        return found


def _render(text: str, subs: dict[str, str]) -> str:
    """Substitute `{name}` placeholders, failing loudly on anything missing.

    A silent fallback would ship cards reading "scan the {collection}" to real
    learners, so an unsupplied noun is an error at build time — the same
    fail-fast posture `CardStore` takes with malformed cards.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in subs:
            raise MissingSubstitution(name)
        return subs[name]

    return _PLACEHOLDER.sub(replace, text)


def render_all(items, subs: dict[str, str]):
    """Render a tuple of strings or of flat string dicts."""
    out = []
    for item in items:
        if isinstance(item, str):
            out.append(_render(item, subs))
        else:
            out.append({k: _render(v, subs) for k, v in item.items()})
    return out


# --- the library -------------------------------------------------------------

_REGISTRY: dict[str, Archetype] = {}


def register(a: Archetype) -> Archetype:
    if a.key in _REGISTRY:
        raise ValueError(f"duplicate archetype key: {a.key}")
    _REGISTRY[a.key] = a
    return a


def get(key: str) -> Archetype:
    try:
        return _REGISTRY[key]
    except KeyError:
        raise KeyError(f"unknown archetype {key!r}; known: {', '.join(sorted(_REGISTRY))}")


def keys() -> list[str]:
    return sorted(_REGISTRY)


def all_archetypes() -> list[Archetype]:
    return [_REGISTRY[k] for k in keys()]
