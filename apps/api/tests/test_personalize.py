"""Hints that are about the learner's code, not just about the problem.

Two properties matter here and pull against each other: the observation has to
be *true of this code* (or it reads as a tool that isn't looking), and it has to
*vary* (or the ladder reads as canned however true each line is). The second was
the live defect — four consecutive hints opening "There's state being mutated
inside the loop."
"""

from __future__ import annotations

import pytest

from leetlearn.analysis import analyze
from leetlearn.mentor import personalize
from leetlearn.mentor.contracts import looks_like_code

SAMPLES = {
    "brute_force": "def f(nums, t):\n"
                   "    for i in range(len(nums)):\n"
                   "        for j in range(i+1, len(nums)):\n"
                   "            if nums[i] + nums[j] == t: return [i, j]\n",
    "hash_one_pass": "def f(nums, t):\n"
                     "    seen = {}\n"
                     "    for i, x in enumerate(nums):\n"
                     "        if t - x in seen: return [seen[t-x], i]\n"
                     "        seen[x] = i\n",
    "two_pointer": "def f(s, t):\n"
                   "    c1 = 0\n"
                   "    c2 = 0\n"
                   "    while c1 < len(s) and c2 < len(t):\n"
                   "        if s[c1] == t[c2]: c1 += 1\n"
                   "        c2 += 1\n"
                   "    return c1 == len(s)\n",
    "memoised": "def climb(n, memo={}):\n"
                "    if n in memo: return memo[n]\n"
                "    memo[n] = climb(n-1) + climb(n-2)\n"
                "    return memo[n]\n",
    "unmemoised": "def climb(n):\n    if n < 2: return n\n    return climb(n-1) + climb(n-2)\n",
    "three_passes": "def f(a):\n    for x in a: pass\n    for y in a: pass\n    for z in a: pass\n    return a\n",
    "triple_nested": "def f(a):\n"
                     "    for i in a:\n"
                     "        for j in a:\n"
                     "            for k in a:\n"
                     "                pass\n",
    "empty": "class Solution:\n    pass\n",
}


def _signals(name):
    return analyze("python", SAMPLES[name])


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_every_shape_of_code_gets_something_said_about_it(name):
    """Silence is the right answer when observations run out, but never on the
    first hint — that is where the learner decides whether this tool is looking
    at their screen or reciting."""
    assert personalize.lead_in(_signals(name), 0), f"{name} produced no opening observation"


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_consecutive_hints_never_repeat_an_observation(name):
    signals = _signals(name)
    seen = [personalize.lead_in(signals, i) for i in range(4)]
    said = [s for s in seen if s]
    assert len(said) == len(set(said)), f"{name} repeated an observation: {said}"


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_observations_never_read_as_code(name):
    """These get prepended to a ladder rung, so they sit inside the AC gate."""
    for obs in personalize.observe(_signals(name)):
        assert not looks_like_code(obs.text), f"{name}/{obs.key}: {obs.text}"


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_observations_run_out_rather_than_cycling(name):
    """Repetition is worse than silence — a hint padded with an observation the
    learner already read is the canned feel this module exists to remove."""
    signals = personalize.observe(_signals(name))
    assert personalize.lead_in(_signals(name), len(signals)) == ""


def test_the_observation_matches_what_is_actually_there():
    keys = lambda n: {o.key for o in personalize.observe(_signals(n))}
    assert "nested_no_lookup" in keys("brute_force")
    assert "single_pass_lookup" in keys("hash_one_pass")
    assert "recursion_no_memo" in keys("unmemoised")
    assert "recursion_with_memo" in keys("memoised")
    assert "many_flat_passes" in keys("three_passes")
    assert "deep_nesting" in keys("triple_nested")
    assert "barely_started" in keys("empty")


def test_a_numbered_pointer_pair_counts_as_tracking_positions():
    """`c1`/`c2` is a textbook two-pointer and a fixed vocabulary of index names
    misses every numbered variant of it."""
    assert "multiple_positions" in {o.key for o in personalize.observe(_signals("two_pointer"))}


def test_value_variables_are_not_mistaken_for_positions():
    signals = analyze("python", "def f(nums2, sum1):\n    for x in nums2: sum1 += x\n    return sum1\n")
    assert "multiple_positions" not in {o.key for o in personalize.observe(signals)}


def test_memoised_recursion_is_not_told_it_forgot_to_memoise():
    keys = {o.key for o in personalize.observe(_signals("memoised"))}
    assert "recursion_no_memo" not in keys


def test_unparseable_code_produces_no_observations():
    """Inventing an observation about code we could not read is the one failure
    mode worse than saying nothing."""
    assert personalize.observe(analyze("python", "def f( this is not python")) == []
    assert personalize.lead_in(analyze("python", "def f( nope"), 0) == ""


def test_observations_are_ranked_strongest_first():
    for name in SAMPLES:
        weights = [o.weight for o in personalize.observe(_signals(name))]
        assert weights == sorted(weights, reverse=True), name


def test_compose_leads_with_the_observation_then_the_rung():
    signals = _signals("brute_force")
    out = personalize.compose("Consider what you already know.", signals, seen=0)
    assert out.startswith(personalize.lead_in(signals, 0))
    assert out.endswith("Consider what you already know.")
