"""Interview mode: probes generated from the learner's own submission.

Two properties matter here. The questions must be about the code that was
actually written — a fixed question list is a quiz, not an interview. And the
model answers must not travel with the questions, because the entire value of
the exercise is in committing to an answer before seeing a good one.
"""

from __future__ import annotations

import pytest

from alfred.analysis import analyze
from alfred.mentor import probes
from alfred.mentor.cards import CardStore
from alfred.mentor.service import HintGateError
from alfred.models import Session, utcnow

HASH_MAP = (
    "def twoSum(nums, target):\n"
    "    seen = {}\n"
    "    for i, x in enumerate(nums):\n"
    "        if target - x in seen:\n"
    "            return [seen[target - x], i]\n"
    "        seen[x] = i"
)
BRUTE_FORCE = (
    "def twoSum(nums, target):\n"
    "    for i in range(len(nums)):\n"
    "        for j in range(i + 1, len(nums)):\n"
    "            if nums[i] + nums[j] == target:\n"
    "                return [i, j]"
)
UNMEMOISED = (
    "def fib(n):\n"
    "    if n < 2:\n"
    "        return n\n"
    "    return fib(n - 1) + fib(n - 2)"
)


@pytest.fixture
def card():
    return CardStore().load_dir().get("two-sum")


def _solved(db, user, slug="two-sum"):
    s = Session(user_id=user.id, slug=slug, language="python", solved_at=utcnow())
    db.add(s)
    db.commit()
    return s


def _keys(card, code):
    return {p.key for p in probes.generate(card, analyze("python", code))}


# --- probes follow the code --------------------------------------------------


def test_hash_solution_is_asked_about_collisions(card):
    assert "hash_worst_case" in _keys(card, HASH_MAP)


def test_brute_force_is_asked_where_it_stops_scaling(card):
    keys = _keys(card, BRUTE_FORCE)
    assert "scale_ceiling" in keys
    # It has no lookup structure, so the collision question would be nonsense.
    assert "hash_worst_case" not in keys


def test_unmemoised_recursion_is_asked_about_the_call_tree(card):
    keys = _keys(card, UNMEMOISED)
    assert "call_tree_size" in keys
    assert "memo_state" not in keys


def test_different_solutions_get_different_interviews(card):
    """The point of the feature. A fixed list would be a quiz."""
    assert _keys(card, HASH_MAP) != _keys(card, BRUTE_FORCE)


def test_unparseable_code_falls_back_to_explaining_the_approach(card):
    signals = analyze("python", "def broken(:")
    generated = probes.generate(card, signals)
    assert [p.key for p in generated] == ["explain_approach"]


def test_every_probe_carries_an_answer_and_a_reason(card):
    for code in (HASH_MAP, BRUTE_FORCE, UNMEMOISED):
        for p in probes.generate(card, analyze("python", code)):
            assert p.question.strip().endswith(("?", ".")), p.key
            assert len(p.model_answer) > 40, f"{p.key} has no usable model answer"
            # `why_asked` teaches the shape of the question, so the learner can
            # anticipate it next time rather than memorising this instance.
            assert p.why_asked, f"{p.key} doesn't say why it's being asked"


def test_probes_are_ordered_most_exposing_first(card):
    generated = probes.generate(card, analyze("python", BRUTE_FORCE))
    weights = [p.weight for p in generated]
    assert weights == sorted(weights, reverse=True)


# --- the gate ----------------------------------------------------------------


def test_interview_is_locked_before_a_passing_submission(db, user, service):
    unsolved = Session(user_id=user.id, slug="two-sum", language="python")
    db.add(unsolved)
    db.commit()
    with pytest.raises(HintGateError):
        service.interview(db, unsolved, HASH_MAP)
    with pytest.raises(HintGateError):
        service.interview_answers(db, unsolved, HASH_MAP)


def test_questions_do_not_leak_their_answers(db, user, service):
    """The answers must not ride along with the questions.

    If they do they are one devtools tab away, and answering-before-seeing is
    the only part of this exercise that does anything.
    """
    s = _solved(db, user)
    questions = service.interview(db, s, HASH_MAP)
    assert questions
    for q in questions:
        assert set(q) == {"key", "question"}


def test_answers_are_available_on_the_second_call(db, user, service):
    s = _solved(db, user)
    questions = service.interview(db, s, HASH_MAP)
    answers = service.interview_answers(db, s, HASH_MAP)

    assert [q["key"] for q in questions] == [a["key"] for a in answers]
    for a in answers:
        assert a["model_answer"] and a["why_asked"]
