"""Failure cases derived from the code the learner actually wrote.

The card's failure gallery covers how people get *this problem* wrong. It is the
same list for everyone who opens the problem, which means it is mostly about
mistakes the reader did not make — and a gallery of other people's bugs teaches
much less than one that says "this specific thing in your code breaks on this
specific input".

So this module reads `CodeSignals` and produces the failures that follow from the
shape on screen. It is post-AC only: every entry describes how working code
fails, which is only a useful thing to hear once the code works.

Each entry keeps the card format — mistake, trigger, expected, actual, why —
because a failure you cannot reproduce is an opinion. The `why` is the part that
carries the teaching: not "this is a red flag" but the mechanism, so the reader
can recognise the shape next time rather than memorising the instance.
"""

from __future__ import annotations

from ..analysis import CodeSignals
from .examples import Example, concrete_trigger

LOOKUP = {"dict", "set", "map", "hashmap", "unordered_map", "counter", "defaultdict"}


def _case(mistake: str, trigger: str, expected: str, actual: str, why: str) -> dict:
    return {"mistake": mistake, "trigger": trigger, "expected": expected,
            "actual": actual, "why": why}


def derive(
    signals: CodeSignals,
    examples: list[Example] | None = None,
    limit: int = 4,
) -> list[dict]:
    """Failure cases implied by this code's shape, most consequential first.

    `examples` are the problem's own worked inputs. Where one fits, it replaces
    the generic description of a trigger: "try s = "axc", t = "ahbgdc"" is a
    thing a learner can act on in ten seconds, and "an input at the top of the
    stated constraints" is a sentence about problems in general.
    """
    if not signals.parsed:
        return []

    examples = examples or []
    out: list[tuple[int, dict]] = []
    depth = signals.max_loop_depth
    has_lookup = any(d.lower() in LOOKUP for d in signals.data_structures)

    def scaled(generic: str) -> str:
        """A trigger about size. The examples are all small, so they cannot
        stand in for one — but naming the shape they share still beats prose."""
        if examples:
            names = ", ".join(examples[0].args)
            return f"a much larger {names} than the examples give you"
        return generic

    if signals.has_recursion and not signals.has_memoization:
        out.append((100, _case(
            "Recursing without remembering results",
            scaled("an input large enough that the same subproblem recurs — often n around 40"),
            "an answer in well under a second",
            "no answer at all, or a stack overflow",
            "Each call spawns more calls that redo work an earlier branch already "
            "finished, so the cost doubles with every step of n rather than growing "
            "with it. The tell is that the same arguments appear at several places "
            "in the call tree: whenever that is possible, the tree branches instead "
            "of collapsing.",
        )))

    if signals.has_recursion:
        out.append((60, _case(
            "Assuming the recursion depth is safe",
            "a degenerate input — a linked list or tree of 10,000 nodes in one line",
            "the correct result",
            "RecursionError, or a segfault in a compiled language",
            "Recursion depth follows the *shape* of the input, not its size. A "
            "balanced tree of a million nodes recurses about twenty deep; a "
            "thousand-node tree that is really a chain recurses a thousand deep. "
            "The inputs that break this are the ones that do not look like the "
            "picture in the problem statement.",
        )))

    if depth >= 2:
        out.append((90, _case(
            f"Looping {depth} deep over the same data",
            scaled("an input at the top of the stated constraints"),
            "a result inside the time limit",
            "Time Limit Exceeded",
            "The judge's sample inputs are small enough that a quadratic solution "
            "and a linear one are indistinguishable, so passing the examples is not "
            "evidence about scale. The question to ask of any inner loop is what it "
            "re-derives that the outer loop already knew — that is the work a "
            "different structure would save.",
        )))

    if has_lookup:
        out.append((70, _case(
            "Recording before checking",
            "an input where one element satisfies the condition against itself",
            "a pair of distinct positions, or no answer",
            "the same position twice",
            "Inserting first means the very next lookup can find the entry you just "
            "wrote. The order of the two operations is the whole of the bug, and it "
            "is invisible on any input where an element cannot match itself — which "
            "is most of them.",
        )))
        out.append((50, _case(
            "Keying by a value that repeats",
            "an input containing the same value more than once",
            "both occurrences accounted for",
            "only the last one, the earlier silently overwritten",
            "A map keyed by value keeps one entry per key by definition. Whether "
            "that is a bug depends entirely on whether the problem cares which "
            "occurrence you found — so it is worth deciding deliberately rather "
            "than discovering it on a failing test.",
        )))

    if signals.mutates_iterated_collection:
        out.append((45, _case(
            "Mutating what you are iterating over",
            "an input where the loop removes or inserts while scanning",
            "every element visited exactly once",
            "elements skipped, or an index error partway through",
            "The loop's position is an index into a structure whose length is "
            "changing underneath it. Nothing announces this — the loop simply ends "
            "early or reads past the end, and the symptom appears far from the "
            "mutation that caused it.",
        )))

    if depth >= 1 and not signals.early_exit:
        out.append((30, _case(
            "Continuing after the answer is settled",
            "an input whose answer is determined by the first few elements",
            "an early return",
            "the correct answer, arrived at slowly",
            "Not a correctness bug, which is why it survives review. It matters "
            "when the loop body has a side effect that keeps firing after the "
            "result is known — the answer stays right and the state does not.",
        )))

    if depth == 0 and not signals.has_recursion:
        out.append((40, _case(
            "Reading the input before checking there is any",
            concrete_trigger(
                [e for e in examples if any(v in ("[]", '""', "0") for v in e.args.values())],
                "an empty input",
            ),
            "the stated result for nothing at all",
            "an index error, or a wrong default",
            "The first access usually happens before any guard, because the guard "
            "is written after the logic it protects. Empty input is the single most "
            "common untested case for exactly this reason.",
        )))

    out.sort(key=lambda entry: -entry[0])
    return [case for _, case in out[:limit]]
