"""The most important tests in the codebase: prove no solution code can reach a
learner before they have a passing submission, at any hint level, through any path.
"""

import json
from pathlib import Path

import pytest

from leetlearn.mentor.cards import CardStore, ProblemCard
from leetlearn.mentor.contracts import PreACHint, looks_like_code
from leetlearn.mentor.service import FULL_SOLUTION_LEVEL, HintGateError
from leetlearn.gamification import progress
from leetlearn.models import Session


def _session(user, slug="two-sum", solved=False):
    s = Session(user_id=user.id, slug=slug, language="python")
    return s


def test_pre_ac_ladder_is_always_code_free(db, user, service, cards):
    """Every ladder level, for every card in the KB, must be prose (no code)."""
    for slug in cards.slugs():
        s = _session(user, slug)
        db.add(s)
        db.commit()
        for level in (1, 2, 3, 4):
            hint = service.get_hint(db, user, s, level)
            assert not looks_like_code(hint.nudge), f"{slug} L{level} leaked code"
            assert hint.source == "card"


def test_full_solution_blocked_before_ac(db, user, service):
    s = _session(user)
    db.add(s)
    db.commit()
    with pytest.raises(HintGateError):
        service.get_hint(db, user, s, FULL_SOLUTION_LEVEL)


def test_full_solution_unlocks_after_ac(db, user, service):
    s = _session(user)
    db.add(s)
    db.commit()
    progress.on_verdict(db, user, s, "Accepted")
    payload = service.post_ac_payload(s)
    # Now — and only now — real code is available.
    assert payload.approaches
    assert any(a.code for a in payload.approaches)


def test_post_ac_payload_blocked_before_ac(db, user, service):
    s = _session(user)
    db.add(s)
    db.commit()
    with pytest.raises(HintGateError):
        service.post_ac_payload(s)


def test_pre_ac_hint_schema_rejects_code_defense_in_depth():
    """Even if a card or model tried to smuggle code into a nudge, the response
    model refuses to construct."""
    with pytest.raises(ValueError):
        PreACHint(level=2, nudge="def solve():\n    return sum(x for x in nums)")


def test_card_with_code_in_ladder_is_rejected_at_load(tmp_path):
    """A poisoned card (code in the L1-L4 ladder) must fail validation, not
    silently enter the KB."""
    bad = {
        "slug": "bad",
        "title": "Bad",
        "difficulty": "Easy",
        "hint_ladder": {
            "l1": "for i in range(n):\n    return i",
            "l2": "fine",
            "l3": "fine",
            "l4": "fine",
        },
    }
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        CardStore().load_dir(tmp_path)


def test_review_blocked_before_ac(db, user, service):
    s = _session(user)
    db.add(s)
    db.commit()
    with pytest.raises(HintGateError):
        service.review(s, "def twoSum(nums, target): ...")
