"""The knowledge base as shipped.

`test_archetypes.py` proves the machinery is sound on synthetic specs. This
proves the actual cards learners will receive are sound — every one of them,
every time the suite runs. Content is where review gets lax, so the gate is
enforced mechanically rather than by re-reading prose.
"""

from __future__ import annotations

import pytest

from alfred.mentor.cards import CardStore
from alfred.mentor.contracts import looks_like_code


@pytest.fixture(scope="module")
def store():
    return CardStore().load_dir()


@pytest.fixture(scope="module")
def all_cards(store):
    return [store.get(s) for s in store.slugs()]


def test_the_kb_is_not_a_stub(store):
    assert len(store) >= 15, "the KB shrank — a spec probably failed to build"


def test_every_ladder_rung_is_code_free(all_cards):
    """The AC gate, applied to the shipped KB rather than to test fixtures."""
    for card in all_cards:
        for level in (1, 2, 3, 4):
            rung = card.hint_ladder.level(level)
            assert not looks_like_code(rung), f"{card.slug} L{level} reads as code"


def test_the_pre_ac_restatement_never_contains_code(all_cards):
    """`understanding` is shown before the problem is solved."""
    for card in all_cards:
        assert not looks_like_code(card.understanding), f"{card.slug} understanding has code"


def test_every_card_has_a_full_teaching_surface(all_cards):
    for card in all_cards:
        assert card.title and card.difficulty, card.slug
        assert card.approaches, f"{card.slug} has no approaches"
        assert card.pitfalls, f"{card.slug} has no pitfalls"
        assert card.failure_cases, f"{card.slug} has no failure cases"
        assert card.edge_cases, f"{card.slug} has no edge cases"
        assert card.rewrite_challenges, f"{card.slug} has no rewrite challenges"
        assert card.complexity.get("target_time"), f"{card.slug} has no target complexity"


def test_difficulty_is_one_of_the_three(all_cards):
    for card in all_cards:
        assert card.difficulty in {"Easy", "Medium", "Hard"}, f"{card.slug}: {card.difficulty}"


def test_at_least_one_approach_per_card_carries_code(all_cards):
    """Approaches without code still teach a trade-off, but a card where *no*
    approach has code gives a learner nothing concrete post-AC."""
    for card in all_cards:
        assert any(a.code for a in card.approaches), f"{card.slug} has no solution code at all"


def test_solution_code_is_not_reachable_through_a_pre_ac_field(all_cards):
    """Belt and braces on the gate: code lives only on approaches, which the
    serving layer withholds until `solved_at` is set."""
    for card in all_cards:
        pre_ac_text = " ".join(
            [card.understanding, *[p.name for p in card.patterns],
             *[card.hint_ladder.level(i) for i in (1, 2, 3, 4)]]
        )
        assert not looks_like_code(pre_ac_text), f"{card.slug} leaks code pre-AC"


def test_slugs_are_unique_and_url_shaped(store):
    for slug in store.slugs():
        assert slug == slug.lower(), slug
        assert " " not in slug, slug


def test_hand_written_cards_win_over_generated_ones(store):
    """A generalised archetype must never silently replace a card that was
    checked line by line."""
    for slug in ("two-sum", "valid-parentheses"):
        assert store.get(slug).generated_by is None, f"{slug} was overwritten by an archetype"
