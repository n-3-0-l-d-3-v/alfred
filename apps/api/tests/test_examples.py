"""Parsing the worked examples out of a problem statement.

These are the only ground truth the product has about a problem's actual
semantics — the archetype knows the pattern and the analyser knows the code's
shape, but neither knows what this problem returns for any specific input.

The parser is deliberately forgiving and always optional, so the tests care most
about the failure direction: a missed example costs a little specificity, while a
mis-parsed one puts a wrong claim about expected output in front of a learner.
"""

from __future__ import annotations

import pytest

from leetlearn.mentor.examples import Example, concrete_trigger, parse

IS_SUBSEQUENCE = (
    'Given two strings s and t, return true if s is a subsequence of t. '
    'Example 1: Input: s = "abc", t = "ahbgdc" Output: true '
    'Example 2: Input: s = "axc", t = "ahbgdc" Output: false '
    'Constraints: 0 <= s.length <= 100'
)
TWO_SUM = (
    "Given an array of integers nums and an integer target, return indices. "
    "Example 1: Input: nums = [2,7,11,15], target = 9 Output: [0,1] "
    "Explanation: Because nums[0] + nums[1] == 9, we return [0, 1]. "
    "Example 2: Input: nums = [3,2,4], target = 6 Output: [1,2]"
)


def test_reads_both_arguments_and_the_output():
    got = parse(IS_SUBSEQUENCE)
    assert len(got) == 2
    assert got[0].args == {"s": '"abc"', "t": '"ahbgdc"'}
    assert got[0].output == "true"
    assert got[1].output == "false"


def test_a_list_literal_is_one_argument_not_four():
    """Splitting the argument list on every comma is wrong the moment a list
    shows up: "nums = [2,7,11,15], target = 9" is two arguments."""
    got = parse(TWO_SUM)
    assert got[0].args == {"nums": "[2,7,11,15]", "target": "9"}
    assert got[0].output == "[0,1]"


def test_explanations_attach_to_the_right_example():
    got = parse(TWO_SUM)
    assert got[0].explanation and "nums[0] + nums[1] == 9" in got[0].explanation
    assert got[1].explanation is None


def test_the_output_stops_before_the_explanation():
    """Greedy matching would swallow the explanation into the output and quote
    a paragraph where a value belongs."""
    assert parse(TWO_SUM)[0].output == "[0,1]"


def test_constraints_are_not_mistaken_for_an_example():
    for example in parse(IS_SUBSEQUENCE):
        assert "Constraints" not in example.output
        assert "<=" not in example.output


def test_rendering_round_trips_to_something_pasteable():
    assert parse(IS_SUBSEQUENCE)[0].render_input() == 's = "abc", t = "ahbgdc"'


def test_nothing_in_nothing_out():
    assert parse(None) == []
    assert parse("") == []
    assert parse("A problem with no examples at all. Constraints: n >= 1") == []


def test_prose_that_merely_mentions_input_is_not_an_example():
    assert parse("The Input: is described above. Output: should be returned.") == []


def test_oversized_examples_are_dropped_not_truncated():
    """A 40-element array pasted into a failure case makes the case unreadable,
    which defeats the point of quoting a concrete input."""
    huge = "Example 1: Input: nums = [" + ",".join(str(i) for i in range(200)) + "] Output: 1"
    assert parse(huge) == []


def test_the_example_limit_is_respected():
    many = " ".join(f"Example {i}: Input: n = {i} Output: {i}" for i in range(1, 9))
    assert len(parse(many, limit=3)) == 3


def test_concrete_trigger_prefers_a_real_input():
    assert concrete_trigger(parse(IS_SUBSEQUENCE), "some input") == 's = "abc", t = "ahbgdc"'


def test_concrete_trigger_falls_back_rather_than_inventing():
    """A fabricated input that does not match the problem's actual signature is
    specific and wrong, which is worse than vague and true."""
    assert concrete_trigger([], "an input where one value repeats") == "an input where one value repeats"


@pytest.mark.parametrize("statement", [IS_SUBSEQUENCE, TWO_SUM])
def test_every_parsed_example_is_usable(statement):
    for example in parse(statement):
        assert example.is_usable
        assert example.render_input()
        assert example.output


def test_examples_reach_the_review(db, user, service):
    from leetlearn.models import Session, utcnow
    from leetlearn import problem_meta

    problem_meta.remember(db, platform="leetcode", slug="two-sum", statement=TWO_SUM)
    s = Session(user_id=user.id, slug="two-sum", language="python")
    s.solved_at = utcnow()
    db.add(s)
    db.commit()

    r = service.review(db, s, "def f(nums, t):\n    for i in nums:\n        pass\n    return []\n")
    assert [e["input"] for e in r.worked_examples] == [
        "nums = [2,7,11,15], target = 9",
        "nums = [3,2,4], target = 6",
    ]


def test_a_statement_we_never_stored_still_reviews(db, user, service):
    """Examples are an enrichment, never a requirement."""
    from leetlearn.models import Session, utcnow

    s = Session(user_id=user.id, slug="two-sum", language="python")
    s.solved_at = utcnow()
    db.add(s)
    db.commit()
    r = service.review(db, s, "def f(nums, t):\n    return []\n")
    assert r.worked_examples == []
    assert r.headline
