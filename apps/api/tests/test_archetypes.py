"""The archetype library and the card builder.

The library is content, and content is exactly where review gets lax — 29
patterns of prose is more than anyone re-reads carefully on every change. These
tests hold the whole library to the AC gate mechanically, so a ladder rung that
drifts toward giving the answer fails the build rather than reaching a learner.
"""

from __future__ import annotations

import re

import pytest

from leetlearn.mentor import archetype_library  # noqa: F401  (registers the library)
from leetlearn.mentor import archetypes
from leetlearn.mentor.card_builder import Spec, build, build_all
from leetlearn.mentor.cards import CardStore
from leetlearn.mentor.contracts import looks_like_code

# Deliberately code-shaped substitutions. If a template can be pushed into
# looking like code by its nouns, this is what finds it.
HOSTILE_SUBS = {
    "collection": "nums[]",
    "unit": "nums[i]",
    "goal": "target - x",
    "relationship": "nums[i] + nums[j] == target",
    "condition": "count[c] <= k",
    "width": "k",
}

PLAIN_SUBS = {
    "collection": "the array",
    "unit": "element",
    "goal": "the target",
    "relationship": "the needed complement",
    "condition": "the constraint",
    "width": "k",
}


def _every_archetype():
    return archetypes.all_archetypes()


def test_library_is_populated():
    assert len(_every_archetype()) >= 25


@pytest.mark.parametrize("arch", _every_archetype(), ids=lambda a: a.key)
def test_ladder_is_code_free_under_plain_nouns(arch):
    for level, text in arch.ladder.render(PLAIN_SUBS).items():
        assert not looks_like_code(text), f"{arch.key}.{level} reads as code: {text}"


@pytest.mark.parametrize("arch", _every_archetype(), ids=lambda a: a.key)
def test_ladder_is_code_free_under_hostile_nouns(arch):
    """A card must not be able to smuggle code in through its substitutions.

    Specializations are the least-reviewed part of the system — one line of
    nouns per problem — so the templates have to hold up even when those nouns
    are themselves code-shaped.
    """
    for level, text in arch.ladder.render(HOSTILE_SUBS).items():
        assert not looks_like_code(text), f"{arch.key}.{level} reads as code: {text}"


@pytest.mark.parametrize("arch", _every_archetype(), ids=lambda a: a.key)
def test_ladder_rungs_are_substantial(arch):
    """A rung too short to teach anything is worse than no rung — it burns a
    hint from the learner's daily budget and returns nothing."""
    for level, text in arch.ladder.render(PLAIN_SUBS).items():
        assert len(text) >= 60, f"{arch.key}.{level} is too short to be useful"


@pytest.mark.parametrize("arch", _every_archetype(), ids=lambda a: a.key)
def test_archetype_carries_a_full_teaching_surface(arch):
    assert arch.approaches, f"{arch.key} has no approaches"
    assert len(arch.pitfalls) >= 3, f"{arch.key} needs at least 3 pitfalls"
    assert len(arch.failure_cases) >= 2, f"{arch.key} needs at least 2 failure cases"
    assert len(arch.edge_cases) >= 3, f"{arch.key} needs at least 3 edge cases"
    assert len(arch.rewrite_challenges) >= 3, f"{arch.key} needs at least 3 rewrites"


@pytest.mark.parametrize("arch", _every_archetype(), ids=lambda a: a.key)
def test_failure_cases_are_concrete(arch):
    """Each failure case must state what breaks, what you wanted, and what you
    actually get. An abstract warning is the thing this feature exists to replace."""
    for case in arch.failure_cases:
        assert set(case) == {"mistake", "trigger", "expected", "actual", "why"}, (
            f"{arch.key} failure case has the wrong shape: {sorted(case)}"
        )
        assert case["expected"] != case["actual"], f"{arch.key} failure case shows no failure"


@pytest.mark.parametrize("arch", _every_archetype(), ids=lambda a: a.key)
def test_pattern_hint_does_not_name_the_technique(arch):
    """Pre-AC the panel shows `pattern_hint`. Naming the exact data structure to
    someone who hasn't solved it yet hands over most of the answer, which is
    precisely what the AC gate exists to prevent."""
    if not arch.pattern_hint:
        return
    banned = ("hash map", "hash table", "binary search", "dynamic programming",
              "monotonic stack", "union find", "trie", "heap", "backtracking")
    lowered = arch.pattern_hint.lower()
    assert not any(b in lowered for b in banned), (
        f"{arch.key} pattern_hint names the technique: {arch.pattern_hint!r}"
    )


# --- the builder -------------------------------------------------------------


def _spec(**over) -> Spec:
    base = dict(
        slug="demo",
        title="Demo Problem",
        difficulty="Easy",
        archetype="hash-lookup",
        subs=PLAIN_SUBS,
        understanding="A plain restatement of the demo problem.",
    )
    base.update(over)
    return Spec(**base)


def test_build_produces_a_valid_card():
    card = build(_spec())
    assert card.slug == "demo"
    assert card.complexity["target_time"] == "O(n)"
    assert card.generated_by == "archetype:hash-lookup"
    assert card.hint_ladder.level(1)
    assert card.pitfalls and card.failure_cases and card.edge_cases


def test_missing_substitution_fails_loudly():
    """Better a build error than a card telling a learner to scan the {collection}."""
    with pytest.raises(archetypes.MissingSubstitution) as exc:
        build(_spec(subs={"collection": "the array"}))
    assert "demo" in str(exc.value)


def test_unknown_archetype_is_rejected():
    with pytest.raises(KeyError):
        build(_spec(archetype="no-such-pattern"))


def test_code_attaches_only_to_named_approaches():
    card = build(_spec(code={"One-pass hash map": "def f(): pass"}))
    by_name = {a.name: a for a in card.approaches}
    assert by_name["One-pass hash map"].code == "def f(): pass"
    # An approach without code is still worth listing — the trade-off teaches
    # even when the implementation is left out.
    assert by_name["Brute force (compare every pair)"].code is None


def test_overrides_replace_generated_fields():
    card = build(_spec(overrides={"edge_cases": ["only this one"]}))
    assert card.edge_cases == ["only this one"]


def test_an_override_cannot_smuggle_code_into_the_ladder():
    """The override escape hatch must not become a hole in the AC gate."""
    with pytest.raises(ValueError):
        build(_spec(overrides={"hint_ladder": {
            "l1": "def solve(nums):\n    return sorted(nums)",
            "l2": "x = 1\ny = 2",
            "l3": "fine",
            "l4": "fine",
        }}))


def test_extras_append_rather_than_replace():
    generated = build(_spec())
    card = build(_spec(extra_edge_cases=("a problem-specific case",)))
    assert len(card.edge_cases) == len(generated.edge_cases) + 1
    assert card.edge_cases[-1] == "a problem-specific case"


def test_build_all_reports_every_failure_at_once():
    """Authoring 150 cards one error at a time would be needlessly serial."""
    with pytest.raises(ValueError) as exc:
        build_all([
            _spec(slug="bad-one", subs={}),
            _spec(slug="bad-two", archetype="nope"),
            _spec(slug="fine"),
        ])
    message = str(exc.value)
    assert "bad-one" in message and "bad-two" in message


@pytest.mark.parametrize("arch", _every_archetype(), ids=lambda a: a.key)
def test_every_archetype_can_build_a_loadable_card(arch):
    """End to end: each pattern must produce a card that passes ProblemCard
    validation, which is what CardStore runs at startup."""
    card = build(_spec(slug=f"demo-{arch.key}", archetype=arch.key, subs=PLAIN_SUBS))
    assert card.hint_ladder.level(4)
    assert card.complexity["target_time"]


# --- article agreement -------------------------------------------------------

# Nouns are written with their article ("the array") because most templates read
# "walk through {collection}". Templates that supply their own article rendered
# as "An empty the array", which shipped on most cards in the library — the kind
# of defect that survives review because template and noun are each correct
# alone and only wrong together.

DOUBLE_ARTICLE = re.compile(r"\b(?:a|an|the)\s+(?:a|an|the)\b", re.I)


def _all_prose(card):
    texts = [
        card.understanding,
        *(card.hint_ladder.level(i) for i in range(1, 5)),
        *card.edge_cases,
        *card.rewrite_challenges,
        *(a.idea for a in card.approaches),
    ]
    for entry in card.pitfalls + card.failure_cases:
        texts += [str(v) for v in entry.values()]
    return texts


@pytest.mark.parametrize("slug", CardStore().load_dir().slugs())
def test_no_card_renders_a_doubled_article(slug):
    card = CardStore().load_dir().get(slug)
    for text in _all_prose(card):
        match = DOUBLE_ARTICLE.search(text)
        assert not match, f"{slug}: {text[max(0, match.start() - 30):match.end() + 20]!r}"


@pytest.mark.parametrize(
    "template,expected",
    [
        # The template supplies the article; the noun's is dropped.
        ("An empty {collection}", "An empty array"),
        ("An empty or single-element {collection}", "An empty or single-element array"),
        ("The entire {collection}", "The entire array"),
        ("Scan the {collection}", "Scan the array"),
        # A preposition means the earlier article governs a different noun, so
        # the substituted noun keeps its own.
        ("The length of {collection}", "The length of the array"),
        ("Walk through {collection}", "Walk through the array"),
        ("A pass over {collection}", "A pass over the array"),
        # No article in the template at all — nothing to dedupe.
        ("{collection} is sorted", "the array is sorted"),
    ],
)
def test_article_dedup_rules(template, expected):
    assert archetypes.render_all((template,), {"collection": "the array"})[0] == expected


def test_a_becomes_an_when_stripping_leaves_a_vowel():
    """Dropping an article changes the word that follows it, so agreement has to
    be recomputed — otherwise "A {collection}" renders "A array"."""
    assert archetypes.render_all(("A {collection}",), {"collection": "the array"})[0] == "An array"
    assert archetypes.render_all(("An {collection}",), {"collection": "the grid"})[0] == "A grid"
