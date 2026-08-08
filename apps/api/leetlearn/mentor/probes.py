"""Interview probes — questions generated from the learner's own code.

Nobody in a real interview asks you to write Two Sum. They ask why it works,
what it costs, and what breaks it. Reproducing that is the highest-value thing
this product can do after the AC gate, and it costs nothing: every probe below
is selected by static analysis of what the learner actually wrote.

Grading is deliberately self-assessed against a revealed model answer, not
machine-marked. Marking free text needs a model, which needs money, which this
project does not have — and the flashcard evidence is that self-grading against
a good answer works fine when the person is there to learn rather than to be
scored. Committing to an answer *before* seeing the model one is the part that
does the work, so the API hands out questions and answers in separate steps.

Probes are ordered by how much they expose. A question you cannot answer is
worth more than one you can, so the ones targeting known weak spots in the
submitted code come first.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..analysis import CodeSignals
from .cards import ProblemCard


@dataclass(frozen=True)
class Probe:
    key: str
    question: str
    # What a good answer contains. Revealed only after the learner commits to
    # theirs — seeing it first turns the exercise into reading comprehension.
    model_answer: str
    # Why an interviewer asks this, shown alongside the model answer. The point
    # is to teach the shape of the question, not just this instance of it.
    why_asked: str
    weight: int


def _has(signals: CodeSignals, names: set[str]) -> bool:
    return any(d.lower() in names for d in signals.data_structures)


LOOKUPS = {"dict", "set", "map", "hashmap", "unordered_map", "counter", "defaultdict"}


def generate(card: ProblemCard, signals: CodeSignals, limit: int = 4) -> list[Probe]:
    """Probes for this specific submission, most exposing first."""
    probes: list[Probe] = []
    target = str(card.complexity.get("target_time", "")) or "the target"

    if not signals.parsed:
        # Without readable code the only honest questions are about the problem.
        return [
            Probe(
                "explain_approach",
                "Walk me through your approach in three sentences, without reading the code.",
                "A good answer names the core insight, the data structure that exploits it, "
                "and why the result is correct — in that order.",
                "If you cannot say it in three sentences you do not yet own the idea, "
                "you have only got it working.",
                weight=50,
            )
        ][:limit]

    if _has(signals, LOOKUPS):
        probes.append(Probe(
            "hash_worst_case",
            "Your solution leans on a hash structure for constant-time lookups. "
            "What is the worst case, and when does it actually happen?",
            "Lookups degrade to linear when every key collides, making the whole "
            "solution O(n²). In practice this needs adversarial input or a bad hash "
            "— which is exactly why some judges include anti-hash tests, and why "
            "languages with deterministic hashing are vulnerable to them.",
            "Almost everyone says O(1) without qualification. The qualification is "
            "the thing being tested.",
            weight=80,
        ))

    if signals.max_loop_depth >= 2:
        probes.append(Probe(
            "scale_ceiling",
            f"Your solution runs in {signals.estimated_time_complexity()}. At roughly "
            "what input size does it stop finishing in a second, and show your working.",
            "Assume about 10⁸ simple operations per second. A quadratic solution "
            "therefore tops out near n = 10⁴. Compare that against the problem's "
            "stated constraints — if they exceed it, you passed on luck.",
            "Interviewers want to see you connect complexity to a real number, "
            "not just name a class.",
            weight=85,
        ))

    if signals.has_recursion:
        if signals.has_memoization:
            probes.append(Probe(
                "memo_state",
                "What exactly is your memo keyed on, and how do you know that key "
                "captures the entire state of a subproblem?",
                "The key must include every variable the result depends on. Miss one "
                "and you return a cached answer computed under different conditions — "
                "which produces wrong answers that look like correct ones.",
                "Under-keyed memoisation is the most common silent DP bug, and it "
                "passes small tests happily.",
                weight=88,
            ))
        else:
            probes.append(Probe(
                "call_tree_size",
                "Your recursion has no memo. Roughly how many calls does it make, "
                "and what does that mean for the largest allowed input?",
                "Branching recursion without caching is exponential in the depth — "
                "the same subproblems are recomputed along every path. At the usual "
                "constraints that is more calls than there are seconds in the "
                "universe, so it only survives because the tests are small.",
                "The gap between 'it works' and 'it scales' is where most candidates "
                "get caught.",
                weight=90,
            ))

    if signals.early_exit:
        probes.append(Probe(
            "early_exit_invariant",
            "You return the moment you find a match. Prove that is safe — what "
            "guarantees a later iteration could not have produced a better answer?",
            "It is safe only if the problem asks for any valid answer, or if the "
            "iteration order guarantees the first hit is optimal. If neither holds, "
            "the early return is a bug that happens to pass the given tests.",
            "Returning early is usually right and occasionally catastrophically "
            "wrong. Interviewers check you know which case you are in.",
            weight=75,
        ))

    if signals.mutation_in_loop:
        probes.append(Probe(
            "mutation_invariant",
            "You mutate state inside the loop. State the invariant that holds at "
            "the top of every iteration.",
            "A loop invariant is a statement true before the loop, preserved by each "
            "iteration, and strong enough at exit to imply the result. If you cannot "
            "state one, you do not yet have an argument that the loop is correct — "
            "only evidence that it passed.",
            "This separates people who reason about loops from people who adjust "
            "them until the tests go green.",
            weight=70,
        ))

    probes.append(Probe(
        "space_cost",
        "What is the space complexity, and what would you give up to make it O(1)?",
        f"Name the structures that grow with the input. Getting to constant space "
        f"usually means sorting first, mutating the input, or accepting a worse time "
        f"bound — the target here is {target}, so say which trade you would take.",
        "Space is the half of the analysis most people skip, so asking it is cheap "
        "signal.",
        weight=45,
    ))

    if card.edge_cases:
        probes.append(Probe(
            "edge_case",
            f"Which of these does your code handle least gracefully: "
            f"{'; '.join(card.edge_cases[:3])}?",
            "Trace one of them by hand rather than guessing. The useful answer names "
            "the specific line that would misbehave and what it would return.",
            "Interviewers rarely want the happy path — they want to see whether you "
            "test your own work before they do.",
            weight=60,
        ))

    return sorted(probes, key=lambda p: -p.weight)[:limit]
