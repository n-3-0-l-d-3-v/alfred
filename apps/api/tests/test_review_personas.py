"""Coverage for the teaching surface: multi-language parsing, review lenses,
personas, the failure gallery, and meme tone-gating."""

import pytest

from alfred.analysis import analyze
from alfred.analysis.registry import supported_languages
from alfred.mentor import personas, reactions
from alfred.gamification import progress
from alfred.models import Session, utcnow


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
    r = service.review(db, s, BRUTE_FORCE)
    assert {sec.lens for sec in r.sections} == {"correctness", "complexity", "robustness", "alternatives"}


def test_review_always_says_what_went_well(db, user, service):
    """A pure fault list teaches badly — there must always be positive signal."""
    s = _solved(db, user)
    for code in (BRUTE_FORCE, OPTIMAL, "!!! not parseable !!!"):
        assert service.review(db, s, code).what_you_did_well


def test_failure_gallery_is_concrete(db, user, service):
    """'What happens if you do it wrong' must show a real input and real output."""
    s = _solved(db, user)
    gallery = service.review(db, s, OPTIMAL).failure_gallery
    assert len(gallery) >= 3
    for case in gallery:
        assert case.trigger and case.expected and case.actual and case.why
        assert case.expected != case.actual


def test_alternatives_lens_lists_every_approach(db, user, service):
    s = _solved(db, user)
    alts = next(sec for sec in service.review(db, s, OPTIMAL).sections if sec.lens == "alternatives")
    assert len(alts.findings) == 3  # brute force, hash map, sort+two-pointers


def test_optimal_solution_recognized(db, user, service):
    s = _solved(db, user)
    r = service.review(db, s, OPTIMAL)
    assert r.verdict == "optimal"
    assert r.complexity_time == "O(n)"


def test_unparseable_code_degrades_gracefully(db, user, service):
    s = _solved(db, user)
    r = service.review(db, s, "this is not code at all {{{")
    assert r.verdict == "unknown"
    assert r.failure_gallery  # card content still teaches


# --- personas ---------------------------------------------------------------


def test_every_persona_produces_a_distinct_headline(db, user, service):
    s = _solved(db, user)
    headlines = {p: service.review(db, s, BRUTE_FORCE, persona=p).headline for p in personas.ALL}
    assert len(set(headlines.values())) == len(personas.ALL)


def test_personas_share_identical_findings(db, user, service):
    """Voice may change; technical findings must not — otherwise picking a fun
    persona would give you worse information.

    Compared per lens rather than per position, because a persona reorders the
    sections and retitles them. That reordering *is* the voice: which lens leads
    says what this reader thinks matters first. What must not move is the
    content of any given lens.
    """
    s = _solved(db, user)
    baseline = {sec.lens: sec.findings for sec in service.review(db, s, BRUTE_FORCE, persona="mentor").sections}
    for p in personas.ALL:
        got = {sec.lens: sec.findings for sec in service.review(db, s, BRUTE_FORCE, persona=p).sections}
        assert got == baseline, f"persona {p} changed the findings, not just the voice"


def test_personas_reorder_and_retitle_sections(db, user, service):
    """The reordering has to be real, or the persona feature is decorative."""
    s = _solved(db, user)
    mentor = service.review(db, s, BRUTE_FORCE, persona="mentor")
    interviewer = service.review(db, s, BRUTE_FORCE, persona="interviewer")

    assert [x.lens for x in mentor.sections] != [x.lens for x in interviewer.sections]
    # An interviewer opens on what you cannot yet defend, not on running time.
    assert interviewer.sections[0].lens == "robustness"
    assert [x.title for x in mentor.sections] != [x.title for x in interviewer.sections]


def test_every_persona_signs_off(db, user, service):
    s = _solved(db, user)
    for p in personas.ALL:
        assert service.review(db, s, BRUTE_FORCE, persona=p).closer, f"{p} has no closing line"


def test_interviewer_persona_asks_questions(db, user, service):
    s = _solved(db, user)
    assert "?" in service.review(db, s, BRUTE_FORCE, persona="interviewer").headline


def test_unknown_persona_falls_back_to_mentor(db, user, service):
    s = _solved(db, user)
    assert service.review(db, s, OPTIMAL, persona="nonsense").persona == "mentor"


# --- reactions ------------------------------------------------------------------


def test_reaction_softens_when_the_learner_struggled():
    """Roast tone must not pile on after a hard session."""
    clean = reactions.pick("nested_loop_when_hashmap_exists", tone="roast", hints_used=0)
    struggled = reactions.pick("nested_loop_when_hashmap_exists", tone="roast", hints_used=4)
    assert clean.intensity == "spicy"
    assert struggled.intensity == "gentle"


def test_encourage_tone_is_always_gentle():
    for hints in (0, 5):
        m = reactions.pick("recursion_no_memo", tone="encourage", hints_used=hints)
        assert m.intensity == "gentle"


def test_failed_attempts_also_soften_tone():
    m = reactions.pick("brute_force_accepted", tone="roast", hints_used=0, failed_attempts=4)
    assert m.intensity == "gentle"


def test_every_reaction_situation_has_all_intensities():
    for situation in reactions.situations():
        for tone, hints in (("encourage", 0), ("roast", 1), ("roast", 0)):
            assert reactions.pick(situation, tone=tone, hints_used=hints) is not None


def test_unknown_reaction_situation_returns_none():
    assert reactions.pick("no_such_situation") is None


def test_review_attaches_a_reaction(db, user, service):
    s = _solved(db, user)
    reaction = service.review(db, s, BRUTE_FORCE).reaction
    assert reaction is not None
    # The stamp is the chip; the line is where the writing lives. An emoji-only
    # reaction is exactly what this replaced, so both have to be present.
    assert reaction["stamp"] and reaction["line"]
    assert reaction["tone"] in {"good", "warn", "bad"}


# --- reviews without a verified target ---------------------------------------

# Cards generated for unauthored problems carry prose where a target complexity
# would be ("better than brute force"), because no honest asymptotic claim can be
# made about a problem nobody has worked. The review used to compare against it
# as though it were a complexity, so every such review said "works — can be
# sharper", including on optimal code.

UNGRADED_SLUG = "some-unauthored-problem"


def _ungraded_session(db, user):
    from alfred.mentor.cards import CardStore
    s = Session(user_id=user.id, slug=UNGRADED_SLUG, language="python", hints_used=0)
    s.solved_at = utcnow()
    db.add(s)
    db.commit()
    return s


def test_no_target_does_not_become_a_suboptimal_verdict(db, user, cards, service):
    """The bug this exists for: an optimal single-pass solution being told it
    could be sharper, on the authority of a target we never had."""
    cards.get_or_synthesize(UNGRADED_SLUG, title="999. Unknown", topics=[])
    s = _ungraded_session(db, user)
    r = service.review(db, s, OPTIMAL)
    assert r.verdict == "works — no target on file"
    assert "sharper" not in r.verdict


def test_no_target_says_so_rather_than_naming_a_fake_one(db, user, cards, service):
    cards.get_or_synthesize(UNGRADED_SLUG, title="999. Unknown", topics=[])
    s = _ungraded_session(db, user)
    r = service.review(db, s, OPTIMAL)
    assert "no verified target" in " ".join(
        f for sec in r.sections if sec.lens == "complexity" for f in sec.findings
    )


def test_no_target_never_claims_a_guaranteed_tle(db, user, cards, service):
    """The TLE warning is a concrete numeric claim. It is only true relative to a
    known target, so without one it must not fire."""
    cards.get_or_synthesize(UNGRADED_SLUG, title="999. Unknown", topics=[])
    s = _ungraded_session(db, user)
    r = service.review(db, s, BRUTE_FORCE)
    robustness = " ".join(
        f for sec in r.sections if sec.lens == "robustness" for f in sec.findings
    )
    assert "guaranteed TLE" not in robustness


@pytest.mark.parametrize("persona", personas.ALL)
def test_every_persona_has_something_to_say_without_a_target(db, user, cards, service, persona):
    cards.get_or_synthesize(UNGRADED_SLUG, title="999. Unknown", topics=[])
    s = _ungraded_session(db, user)
    r = service.review(db, s, OPTIMAL, persona=persona)
    assert r.headline.strip()
    assert "{est}" not in r.headline and "{target}" not in r.headline


def test_an_authored_card_still_grades_normally(db, user, service):
    """The new branch must not swallow the case it was carved out of."""
    s = _solved(db, user)
    assert service.review(db, s, OPTIMAL).verdict == "optimal"
    assert service.review(db, s, BRUTE_FORCE).verdict == "works — can be sharper"
