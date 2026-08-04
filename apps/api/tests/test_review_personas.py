"""Coverage for the teaching surface: multi-language parsing, review lenses,
personas, the failure gallery, and meme tone-gating."""

import pytest

from leetlearn.analysis import analyze
from leetlearn.analysis.registry import supported_languages
from leetlearn.mentor import memes, personas
from leetlearn.gamification import progress
from leetlearn.models import Session


def _solved(db, user, slug="two-sum", hints=0):
    s = Session(user_id=user.id, slug=slug, language="python", hints_used=hints)
    db.add(s)
    db.commit()
    progress.on_verdict(db, user, s, "Accepted")
    return s


BRUTE_FORCE = (
    "for i in range(len(nums)):\n"
    "    for j in range(i+1, len(nums)):\n"
    "        if nums[i]+nums[j]==target:\n"
    "            return [i,j]"
)
OPTIMAL = (
    "seen = {}\n"
    "for i, x in enumerate(nums):\n"
    "    if target - x in seen:\n"
    "        return [seen[target-x], i]\n"
    "    seen[x] = i"
)


# --- multi-language static analysis -----------------------------------------


def test_supported_languages_include_the_big_five():
    langs = supported_languages()
    for expected in ("python", "cpp", "java", "javascript", "go"):
        assert expected in langs


@pytest.mark.parametrize(
    "lang,code,depth",
    [
        ("cpp", "int f(int n){ for(int i=0;i<n;i++){ for(int j=0;j<n;j++){ n++; } } return n; }", 2),
        ("java", "class S{ int f(int n){ for(int i=0;i<n;i++){ n++; } return n; } }", 1),
        ("javascript", "function f(n){ for(let i=0;i<n;i++){ for(let j=0;j<n;j++){ n++ } } }", 2),
        ("go", "func f(n int) { for i:=0;i<n;i++ { n++ } }", 1),
    ],
)
def test_loop_depth_across_languages(lang, code, depth):
    sig = analyze(lang, code)
    assert sig.max_loop_depth == depth, f"{lang}: {sig.error}"


def test_recursion_detected_in_go_and_cpp():
    for lang, code in [
        ("go", "func fib(n int) int { if n<2 { return n }\n return fib(n-1)+fib(n-2) }"),
        ("cpp", "int fib(int n){ if(n<2) return n; return fib(n-1)+fib(n-2); }"),
    ]:
        sig = analyze(lang, code)
        assert sig.has_recursion, lang
        assert "2^n" in sig.estimated_time_complexity()


def test_java_hashmap_recognized_as_dict():
    code = "class S{ void f(){ HashMap<Integer,Integer> m = new HashMap<>(); m.put(1,2); } }"
    assert "dict" in analyze("java", code).data_structures


def test_method_named_set_is_not_mistaken_for_a_set():
    """`seen.set(x)` is a method call, not a Set data structure."""
    code = "function f(nums){ const seen = new Map(); seen.set(1,2); }"
    ds = analyze("javascript", code).data_structures
    assert "dict" in ds
    assert "set" not in ds


# --- review lenses ----------------------------------------------------------


def test_review_has_all_four_lenses(db, user, service):
    s = _solved(db, user)
    r = service.review(s, BRUTE_FORCE)
    assert {sec.lens for sec in r.sections} == {"correctness", "complexity", "robustness", "alternatives"}


def test_review_always_says_what_went_well(db, user, service):
    """A pure fault list teaches badly — there must always be positive signal."""
    s = _solved(db, user)
    for code in (BRUTE_FORCE, OPTIMAL, "!!! not parseable !!!"):
        assert service.review(s, code).what_you_did_well


def test_failure_gallery_is_concrete(db, user, service):
    """'What happens if you do it wrong' must show a real input and real output."""
    s = _solved(db, user)
    gallery = service.review(s, OPTIMAL).failure_gallery
    assert len(gallery) >= 3
    for case in gallery:
        assert case.trigger and case.expected and case.actual and case.why
        assert case.expected != case.actual


def test_alternatives_lens_lists_every_approach(db, user, service):
    s = _solved(db, user)
    alts = next(sec for sec in service.review(s, OPTIMAL).sections if sec.lens == "alternatives")
    assert len(alts.findings) == 3  # brute force, hash map, sort+two-pointers


def test_optimal_solution_recognized(db, user, service):
    s = _solved(db, user)
    r = service.review(s, OPTIMAL)
    assert r.verdict == "optimal"
    assert r.complexity_time == "O(n)"


def test_unparseable_code_degrades_gracefully(db, user, service):
    s = _solved(db, user)
    r = service.review(s, "this is not code at all {{{")
    assert r.verdict == "unknown"
    assert r.failure_gallery  # card content still teaches


# --- personas ---------------------------------------------------------------


def test_every_persona_produces_a_distinct_headline(db, user, service):
    s = _solved(db, user)
    headlines = {p: service.review(s, BRUTE_FORCE, persona=p).headline for p in personas.ALL}
    assert len(set(headlines.values())) == len(personas.ALL)


def test_personas_share_identical_findings(db, user, service):
    """Voice may change; technical findings must not — otherwise picking a fun
    persona would give you worse information."""
    s = _solved(db, user)
    baseline = [sec.findings for sec in service.review(s, BRUTE_FORCE, persona="mentor").sections]
    for p in personas.ALL:
        assert [sec.findings for sec in service.review(s, BRUTE_FORCE, persona=p).sections] == baseline


def test_interviewer_persona_asks_questions(db, user, service):
    s = _solved(db, user)
    assert "?" in service.review(s, BRUTE_FORCE, persona="interviewer").headline


def test_unknown_persona_falls_back_to_mentor(db, user, service):
    s = _solved(db, user)
    assert service.review(s, OPTIMAL, persona="nonsense").persona == "mentor"


# --- memes ------------------------------------------------------------------


def test_meme_softens_when_the_learner_struggled():
    """Roast tone must not pile on after a hard session."""
    clean = memes.pick("nested_loop_when_hashmap_exists", tone="roast", hints_used=0)
    struggled = memes.pick("nested_loop_when_hashmap_exists", tone="roast", hints_used=4)
    assert clean.intensity == "spicy"
    assert struggled.intensity == "gentle"


def test_encourage_tone_is_always_gentle():
    for hints in (0, 5):
        m = memes.pick("recursion_no_memo", tone="encourage", hints_used=hints)
        assert m.intensity == "gentle"


def test_failed_attempts_also_soften_tone():
    m = memes.pick("brute_force_accepted", tone="roast", hints_used=0, failed_attempts=4)
    assert m.intensity == "gentle"


def test_every_meme_situation_has_all_intensities():
    for situation in memes.situations():
        for tone, hints in (("encourage", 0), ("roast", 1), ("roast", 0)):
            assert memes.pick(situation, tone=tone, hints_used=hints) is not None


def test_unknown_meme_situation_returns_none():
    assert memes.pick("no_such_situation") is None


def test_review_attaches_a_meme(db, user, service):
    s = _solved(db, user)
    assert service.review(s, BRUTE_FORCE).meme is not None
