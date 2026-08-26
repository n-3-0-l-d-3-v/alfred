"""Generated cards: do they hold the AC gate, and are they honest about being
generated?

Synthesis is the least-reviewed content path in the product — nobody reads a
card that is assembled at request time for a problem they have never seen. So
the invariants that a human reviewer would catch on a hand-written card have to
be enforced mechanically here instead.
"""

from __future__ import annotations

import pytest

from leetlearn.mentor.cards import CardStore
from leetlearn.mentor.contracts import looks_like_code
from leetlearn.mentor.infer import infer
from leetlearn.mentor.synth import FALLBACK_ARCHETYPE, synthesize

PROBLEMS = [
    ("is-subsequence", "392. Is Subsequence", "Easy",
     ["two-pointers", "string", "dynamic-programming"],
     "given two strings s and t, return true if s is a subsequence of t"),
    ("add-two-numbers", "2. Add Two Numbers", "Medium",
     ["linked-list", "math", "recursion"],
     "two non-empty linked lists representing two non-negative integers"),
    ("lru-cache", "146. LRU Cache", "Medium",
     ["hash-table", "linked-list", "design"],
     "design a data structure, LRU cache, get and put in O(1)"),
    ("number-of-islands", "200. Number of Islands", "Medium",
     ["array", "depth-first-search", "matrix"],
     "grid of 1s land and 0s water, return the number of islands"),
    # The degenerate case: nothing but a slug.
    ("totally-unknown-problem", None, None, [], None),
]


@pytest.mark.parametrize("slug,title,difficulty,topics,statement", PROBLEMS,
                         ids=[p[0] for p in PROBLEMS])
def test_generated_ladder_is_code_free(slug, title, difficulty, topics, statement):
    """The AC gate, on the path nobody reviews by hand.

    `HintLadder` validates this at construction, so a violation raises rather
    than returning — but asserting it here names the invariant at the level it
    actually matters, and catches a future change that relaxes the model.
    """
    card, _ = synthesize(slug, title, difficulty, topics, statement)
    for level in (1, 2, 3, 4):
        text = card.hint_ladder.level(level)
        assert not looks_like_code(text), f"{slug} L{level} reads as code: {text}"
        assert text.strip(), f"{slug} L{level} is empty"


@pytest.mark.parametrize("slug,title,difficulty,topics,statement", PROBLEMS,
                         ids=[p[0] for p in PROBLEMS])
def test_generated_cards_ship_no_solution_code(slug, title, difficulty, topics, statement):
    """Approaches may carry code on a hand-written card, because a human wrote
    and checked it. We cannot generate one that is correct, and a plausible
    wrong solution handed over post-AC is the worst thing this path could do."""
    card, _ = synthesize(slug, title, difficulty, topics, statement)
    assert card.approaches, f"{slug} generated no approaches at all"
    for approach in card.approaches:
        assert approach.code is None, f"{slug} generated code for {approach.name!r}"
        assert approach.idea.strip()
        assert approach.time and approach.space


@pytest.mark.parametrize("slug,title,difficulty,topics,statement", PROBLEMS,
                         ids=[p[0] for p in PROBLEMS])
def test_generated_cards_are_never_marked_verified(slug, title, difficulty, topics, statement):
    card, _ = synthesize(slug, title, difficulty, topics, statement)
    assert card.verified is False
    assert card.generated_by


@pytest.mark.parametrize("slug,title,difficulty,topics,statement", PROBLEMS,
                         ids=[p[0] for p in PROBLEMS])
def test_generated_cards_still_teach(slug, title, difficulty, topics, statement):
    """A card that technically validates but carries nothing to say would pass
    every gate above while being useless — which is the failure mode a purely
    negative test suite invites."""
    card, _ = synthesize(slug, title, difficulty, topics, statement)
    assert card.understanding.strip()
    assert card.pitfalls, f"{slug} has no pitfalls"
    assert card.failure_cases, f"{slug} has no failure cases"
    assert card.edge_cases, f"{slug} has no edge cases"
    assert card.rewrite_challenges, f"{slug} has no rewrite challenges"
    for case in card.failure_cases:
        assert {"mistake", "trigger", "expected", "actual", "why"} <= set(case)


def test_placeholders_are_always_resolved():
    """An unsubstituted `{collection}` reaching a learner is the visible form of
    a missing noun. The builder raises on unknown placeholders, so this guards
    the substitutions table rather than the renderer."""
    for slug, title, difficulty, topics, statement in PROBLEMS:
        card, _ = synthesize(slug, title, difficulty, topics, statement)
        blob = " ".join(
            [card.understanding, *(card.hint_ladder.level(i) for i in range(1, 5)),
             *card.edge_cases, *card.rewrite_challenges,
             *(a.idea for a in card.approaches)]
        )
        assert "{" not in blob and "}" not in blob, f"{slug} has an unrendered placeholder"


def test_an_unrecognised_problem_gets_the_pattern_free_ladder():
    """Not the best-scoring guess. Being taught sliding-window on a problem that
    is not one is worse than being told the pattern is unclear."""
    card, inference = synthesize(
        "is-subsequence", "392. Is Subsequence", "Easy",
        ["two-pointers", "string", "dynamic-programming"],
        "given two strings s and t, return true if s is a subsequence of t",
    )
    assert not inference.confident
    assert card.generated_by.startswith(f"fallback:{FALLBACK_ARCHETYPE}")
    assert "don't have a hand-written card" in card.understanding


def test_a_recognised_problem_is_taught_as_its_pattern():
    card, inference = synthesize(
        "add-two-numbers", "2. Add Two Numbers", "Medium",
        ["linked-list", "math"],
        "two non-empty linked lists representing two non-negative integers",
    )
    assert inference.confident
    assert card.generated_by.startswith("inferred:linked-list-rewiring")


def test_the_pattern_shown_carries_the_real_confidence():
    """The builder stamps a flat 0.85 on an archetype's pattern guess. Showing
    that on a card inferred at 0.40 would be the exact overstatement the
    confidence machinery exists to prevent."""
    card, inference = synthesize(
        "add-two-numbers", "2. Add Two Numbers", "Medium", ["linked-list", "math"],
        "two non-empty linked lists representing two non-negative integers",
    )
    assert card.patterns[0].confidence == pytest.approx(inference.confidence, abs=0.01)


def test_only_one_pattern_is_surfaced():
    """Runner-ups were reliably noise rather than a second opinion — Add Two
    Numbers drew Backtracking off its 'recursion' tag."""
    card, _ = synthesize("add-two-numbers", "2. Add Two Numbers", "Medium",
                         ["linked-list", "math", "recursion"], "two linked lists")
    assert len(card.patterns) == 1


# --- store integration -------------------------------------------------------


def test_authored_cards_win_over_generated_ones():
    store = CardStore().load_dir()
    card = store.get_or_synthesize(
        "two-sum", title="wrong title", difficulty="Hard", topics=["tree"],
        statement="a binary tree problem",
    )
    assert card.verified is True
    assert card.title != "wrong title"
    assert not store.is_synthesized("two-sum")


def test_generated_cards_are_cached_not_rebuilt():
    """The second learner on a problem should get a dictionary read, the same as
    on a curated card."""
    store = CardStore().load_dir()
    first = store.get_or_synthesize("brand-new-problem", topics=["array", "hash-table"],
                                    statement="add up to target")
    second = store.get_or_synthesize("brand-new-problem")
    assert first is second, "a second lookup rebuilt the card instead of reusing it"
    assert store.is_synthesized("brand-new-problem")


def test_the_store_never_fails_to_produce_a_card():
    """The property the whole module exists for: no input dead-ends the panel."""
    store = CardStore().load_dir()
    for slug in ["x", "a-very-long-slug-" * 5, "123", "problem-with-no-tags"]:
        assert store.get_or_synthesize(slug) is not None


def test_a_bad_statement_cannot_smuggle_code_into_a_hint():
    """Statement text is attacker-adjacent input — it comes off a web page. It
    is scored for keywords and must never be echoed into a ladder rung."""
    store = CardStore().load_dir()
    card = store.get_or_synthesize(
        "hostile", title="for i in range(n): ans += nums[i]",
        topics=["array"], statement="def solve(nums): return sorted(nums)[0]",
    )
    for level in (1, 2, 3, 4):
        assert not looks_like_code(card.hint_ladder.level(level))
