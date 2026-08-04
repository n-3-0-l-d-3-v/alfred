"""Rich code review: multiple lenses, a failure gallery, and persona voicing.

Runs entirely offline from `CodeSignals` + the Problem Card. An LLM can enrich
this later, but the baseline is deterministic, free, and instant — which is what
lets reviews stay unlimited even on the free tier.
"""

from __future__ import annotations

from ..analysis import CodeSignals
from . import memes, personas
from .cards import ProblemCard
from .contracts import FailureCase, ReviewSection, RichReview


def _norm(c: str) -> str:
    return c.replace(" ", "").replace("_", "").lower()


def _complexity_lens(signals: CodeSignals, est: str, target: str) -> ReviewSection:
    findings: list[str] = []
    if not signals.parsed:
        findings.append(f"Couldn't parse the source ({signals.error}), so this is card-based only.")
        return ReviewSection(lens="complexity", title="Time & space", findings=findings)

    if _norm(est) == _norm(target):
        findings.append(f"Estimated {est}, which matches the target — no wasted asymptotic work.")
    else:
        findings.append(f"Estimated {est}; the target for this problem is {target}.")
        if signals.max_loop_depth >= 2:
            findings.append(
                f"The {signals.max_loop_depth} nested loops are the cost: each outer step re-scans "
                "the data. A lookup structure usually collapses one of those levels."
            )
        if signals.has_recursion and not signals.has_memoization:
            findings.append(
                "Unmemoized recursion recomputes identical subproblems — the call tree branches "
                "instead of collapsing. Memoize, or rebuild it bottom-up."
            )
    if signals.data_structures:
        findings.append(f"Data structures in play: {', '.join(signals.data_structures)}.")
    return ReviewSection(lens="complexity", title="Time & space", findings=findings)


def _correctness_lens(card: ProblemCard, signals: CodeSignals) -> ReviewSection:
    findings = []
    if signals.parsed and signals.early_exit:
        findings.append("Early exit on a match — good, no wasted iterations after the answer is found.")
    if card.edge_cases:
        findings.append(
            "Worth re-checking against these: " + "; ".join(card.edge_cases[:4]) + "."
        )
    if not findings:
        findings.append("It passes the judge — the core logic is sound.")
    return ReviewSection(lens="correctness", title="Correctness & edges", findings=findings)


def _robustness_lens(signals: CodeSignals, target: str) -> ReviewSection:
    findings = []
    if signals.parsed:
        if signals.max_loop_depth >= 2 and _norm(target) in {"o(n)", "o(nlogn)"}:
            findings.append(
                "At n = 10⁵ this would do ~10¹⁰ operations — a guaranteed TLE. It passed because "
                "these constraints are small, not because the approach scales."
            )
        if signals.has_recursion and not signals.has_memoization:
            findings.append(
                "Deep inputs risk both exponential time and a stack overflow before you ever see a wrong answer."
            )
        if signals.mutation_in_loop:
            findings.append(
                "Mutating state inside the loop is correct here but makes the code harder to reason "
                "about later — the failure mode is a subtle bug during a future edit, not today."
            )
    if not findings:
        findings.append("Nothing here scales badly or mutates surprisingly. It should hold up.")
    return ReviewSection(lens="robustness", title="What would break this", findings=findings)


def _alternatives_lens(card: ProblemCard) -> ReviewSection:
    findings = [
        f"{a.name} — {a.idea} ({a.time} time, {a.space} space)" for a in card.approaches
    ]
    return ReviewSection(lens="alternatives", title="Other ways to solve it", findings=findings)


def build_review(
    card: ProblemCard,
    signals: CodeSignals,
    persona_key: str = personas.MENTOR,
    hints_used: int = 0,
    failed_attempts: int = 0,
) -> RichReview:
    p = personas.get(persona_key)
    target = str(card.complexity.get("target_time", "O(n)"))
    est = signals.estimated_time_complexity()
    optimal = signals.parsed and _norm(est) == _norm(target)

    # --- headline in the persona's voice ---
    if not signals.parsed:
        headline = p.unparsed
    elif optimal:
        headline = p.optimal.format(est=est, target=target)
    else:
        headline = p.suboptimal.format(est=est, target=target)

    # --- which meme situation applies ---
    if not signals.parsed:
        situation = "unparseable"
    elif signals.has_recursion and not signals.has_memoization:
        situation = "recursion_no_memo"
    elif signals.max_loop_depth >= 2 and not optimal:
        situation = "brute_force_accepted" if hints_used == 0 else "nested_loop_when_hashmap_exists"
    elif optimal and hints_used == 0:
        situation = "no_hints_solve"
    elif optimal:
        situation = "clean_solve"
    elif signals.mutation_in_loop:
        situation = "mutation_soup"
    else:
        situation = "hint_heavy_solve" if hints_used >= 3 else "clean_solve"

    meme = memes.pick(situation, tone=p.meme_tone, hints_used=hints_used, failed_attempts=failed_attempts)

    # --- what went well (never skip this; a pure fault list teaches badly) ---
    well: list[str] = []
    if optimal:
        well.append(f"Reached the optimal {est} complexity.")
    # Only *deliberate* structures earn praise. A bare list/tuple literal shows up
    # in almost every solution (`return [i, j]`) and says nothing about intent —
    # praising it on brute-force code reads as hollow.
    deliberate = [d for d in signals.data_structures if d in {"dict", "set", "heap", "deque", "stack"}]
    if signals.parsed and deliberate:
        well.append(f"Reached for {', '.join(deliberate)} rather than brute-forcing the lookup.")
    if hints_used == 0:
        well.append("Solved it with zero hints.")
    elif hints_used <= 2:
        well.append(f"Only needed {hints_used} hint(s) — you were close on your own.")
    if not well:
        well.append("You got a passing submission. That's the part most people don't finish.")

    return RichReview(
        persona=p.key,
        persona_label=p.label,
        headline=headline,
        verdict="optimal" if optimal else ("unknown" if not signals.parsed else "works — can be sharper"),
        complexity_time=est,
        complexity_space="(space estimate needs data-flow analysis — Phase 1.5)",
        target_time=target,
        sections=[
            _complexity_lens(signals, est, target),
            _correctness_lens(card, signals),
            _robustness_lens(signals, target),
            _alternatives_lens(card),
        ],
        failure_gallery=[FailureCase(**fc) for fc in card.failure_cases],
        failure_intro=p.failure_intro,
        what_you_did_well=well,
        try_next=card.rewrite_challenges,
        next_intro=p.next_intro,
        meme=meme.model_dump() if meme else None,
        card_verified=card.verified,
        source="signals",
    )
