"""Failure cases derived from the learner's own code.

The card's gallery is the same list for everyone who opens the problem, so most
of it describes mistakes this reader did not make. These come from the shape on
screen instead. The tests below care about two things: that a case only appears
when the code actually has that shape, and that the `why` teaches a mechanism
rather than flagging a smell.
"""

from __future__ import annotations

import pytest

from leetlearn.analysis import analyze
from leetlearn.mentor import misconceptions
from leetlearn.mentor.contracts import looks_like_code

CODE = {
    "brute_force": "def f(nums, t):\n"
                   "    for i in range(len(nums)):\n"
                   "        for j in range(i+1, len(nums)):\n"
                   "            if nums[i] + nums[j] == t: return [i, j]\n",
    "hash_lookup": "def f(nums, t):\n"
                   "    seen = {}\n"
                   "    for i, x in enumerate(nums):\n"
                   "        if t - x in seen: return [seen[t-x], i]\n"
                   "        seen[x] = i\n",
    "unmemoised": "def climb(n):\n    if n < 2: return n\n    return climb(n-1) + climb(n-2)\n",
    "memoised": "def climb(n, memo={}):\n"
                "    if n in memo: return memo[n]\n"
                "    memo[n] = climb(n-1) + climb(n-2)\n"
                "    return memo[n]\n",
    "straight_line": "def f(a, b):\n    return a + b\n",
}


def _derive(name):
    return misconceptions.derive(analyze("python", CODE[name]))


def _mistakes(name):
    return " | ".join(c["mistake"].lower() for c in _derive(name))


@pytest.mark.parametrize("name", sorted(CODE))
def test_every_case_is_reproducible(name):
    """A failure you cannot reproduce is an opinion. Each case has to name the
    input, what should happen, and what does."""
    for case in _derive(name):
        assert set(case) == {"mistake", "trigger", "expected", "actual", "why"}
        for field, value in case.items():
            assert value.strip(), f"{name}: empty {field}"


@pytest.mark.parametrize("name", sorted(CODE))
def test_cases_never_read_as_code(name):
    """These render post-AC, but the gallery format is shared with the pre-AC
    card, so keeping them prose-only keeps one rule instead of two."""
    for case in _derive(name):
        assert not looks_like_code(case["why"]), case["why"]


@pytest.mark.parametrize("name", sorted(CODE))
def test_the_why_explains_a_mechanism(name):
    """The point of this module: not 'this is a red flag' but why the mistake
    happens, so the reader recognises the shape rather than the instance."""
    for case in _derive(name):
        assert len(case["why"].split()) >= 20, f"{name}: {case['why']!r} is too thin to teach"


def test_unmemoised_recursion_is_called_out():
    assert "remembering results" in _mistakes("unmemoised")


def test_memoised_recursion_is_not_accused_of_forgetting():
    assert "remembering results" not in _mistakes("memoised")


def test_recursion_depth_is_raised_for_any_recursion():
    """Depth follows the shape of the input, not its size — so it applies to
    correctly memoised code too."""
    assert "recursion depth" in _mistakes("memoised")


def test_nested_loops_get_the_scale_warning():
    assert "deep over the same data" in _mistakes("brute_force")


def test_flat_code_does_not_get_the_scale_warning():
    assert "deep over the same data" not in _mistakes("hash_lookup")


def test_lookup_structures_get_the_ordering_trap():
    assert "recording before checking" in _mistakes("hash_lookup")


def test_code_with_no_lookup_does_not():
    assert "recording before checking" not in _mistakes("straight_line")


def test_loopless_code_is_warned_about_empty_input():
    assert "before checking there is any" in _mistakes("straight_line")


def test_unparseable_code_yields_nothing():
    """Inventing a failure case for code we could not read would attach a
    concrete, reproducible-sounding claim to a guess."""
    assert misconceptions.derive(analyze("python", "def f( not python")) == []


def test_the_gallery_is_capped():
    """A wall of failure cases is skimmed, which is the same as not shown."""
    for name in CODE:
        assert len(_derive(name)) <= 4


def test_derived_cases_lead_the_review_gallery(db, user, service):
    """Ordering is the point: a reader should see their own bug before a list of
    other people's."""
    from leetlearn.models import Session, utcnow

    s = Session(user_id=user.id, slug="two-sum", language="python")
    s.solved_at = utcnow()
    db.add(s)
    db.commit()

    gallery = service.review(db, s, CODE["brute_force"]).failure_gallery
    assert "deep over the same data" in gallery[0].mistake.lower()


def test_the_gallery_does_not_repeat_a_mistake(db, user, service):
    """An archetype and the code will often name the same trap."""
    from leetlearn.models import Session, utcnow

    s = Session(user_id=user.id, slug="two-sum", language="python")
    s.solved_at = utcnow()
    db.add(s)
    db.commit()

    mistakes = [c.mistake.strip().lower() for c in service.review(db, s, CODE["hash_lookup"]).failure_gallery]
    assert len(mistakes) == len(set(mistakes))
