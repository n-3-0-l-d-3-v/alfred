"""Make a hint about *this* learner's code rather than about the problem.

The card supplies the teaching content; this module decides which part of it
they get and opens with something only true of what they actually wrote. That
distinction is the whole difference between a hint that feels like a printed
solutions manual and one that feels like someone reading over your shoulder.

Why not just call a model per hint: it costs real money on every keystroke-ish
interaction, and this project has a hard zero-budget constraint. Static analysis
already knows the things a mentor would notice first — how deep the loops go,
whether a lookup structure exists, whether recursion memoises, whether there is
an early exit. Those are exactly the observations that make a hint land, and
they are free.

Everything produced here still passes through `PreACHint`, so the AC gate holds:
observations describe *shape*, never the fix.
"""

from __future__ import annotations

from dataclasses import dataclass

import re

from ..analysis import CodeSignals

# Python's SyntaxError renders as '... (line 4)'; tree-sitter reports a row.
_LINE_RE = re.compile(r'(?:line|row)\s+(\d+)', re.I)

# Structures that represent a deliberate lookup/ordering decision, as opposed to
# a list literal that shows up in nearly every solution and means nothing.
LOOKUP_STRUCTURES = {"dict", "set", "map", "hashmap", "unordered_map", "counter", "defaultdict"}
ORDERED_STRUCTURES = {"heap", "deque", "stack", "queue", "priority_queue"}


@dataclass(frozen=True)
class Observation:
    """Something true about the learner's code, phrased as a mentor would say it.

    `weight` orders competing observations: the higher the number, the more it
    dominates what the learner should think about next. Exactly one is shown per
    hint, because a hint that lists four things is a code review, and a code
    review before you have solved it is the thing this product exists to refuse.
    Successive hints walk down the ranking rather than repeating the top one.
    """

    key: str
    text: str
    weight: int


def _has(signals: CodeSignals, names: set[str]) -> bool:
    return any(d.lower() in names for d in signals.data_structures)


COUNTING_STRUCTURES = {"counter", "defaultdict"}

# Single-letter names conventionally used as positions rather than values. Two
# of them moving through the same data is the visible signature of a
# two-pointer attempt, which is worth naming back to the learner.
_INDEX_NAMES = {"i", "j", "k", "l", "r", "lo", "hi", "left", "right", "slow", "fast",
                "p", "q", "start", "end", "head", "tail", "first", "second",
                "read", "write", "front", "back"}

# `c1`/`c2`, `p1`/`p2`, `idx1`/`idx2` — a numbered pair is one of the commonest
# ways people name two pointers, and a fixed vocabulary list misses all of them.
# Anchored to a short prefix so it does not sweep up `nums2` or `sum1`.
_NUMBERED_INDEX = re.compile(r"^[a-z]{1,3}\d$", re.I)


def _is_position_name(name: str) -> bool:
    return name.lower() in _INDEX_NAMES or bool(_NUMBERED_INDEX.match(name))


def observe(signals: CodeSignals) -> list[Observation]:
    """Everything worth noticing about this code, strongest first.

    Breadth matters here as much as accuracy. A handful of observations means
    most code falls through to the same two or three lines, and a hint that
    opens with the same sentence every time reads as canned however true it is —
    which is the precise failure the module exists to avoid.

    Every observation describes *shape*: what is on screen, not what to do about
    it. That is what keeps the AC gate intact when these are prepended to a
    ladder rung.
    """
    if not signals.parsed:
        return []

    out: list[Observation] = []
    depth = signals.max_loop_depth
    has_lookup = _has(signals, LOOKUP_STRUCTURES)
    has_ordered = _has(signals, ORDERED_STRUCTURES)
    has_counting = _has(signals, COUNTING_STRUCTURES)
    indexes = sorted({v for v in signals.variables if _is_position_name(v)})

    # --- where they are overall ---

    if depth == 0 and not signals.has_recursion and not signals.functions:
        out.append(Observation(
            "barely_started",
            "Not much in the editor yet — no loops, no recursion.",
            weight=95,
        ))

    if signals.has_recursion and not signals.has_memoization:
        out.append(Observation(
            "recursion_no_memo",
            "You're recursing, but nothing is remembering results between calls yet.",
            weight=90,
        ))
    elif signals.has_recursion and signals.has_memoization:
        out.append(Observation(
            "recursion_with_memo",
            "You've got recursion with a table remembering results, so repeated "
            "subproblems are already collapsing rather than branching.",
            weight=55,
        ))

    # --- loop shape ---

    if depth >= 3:
        out.append(Observation(
            "deep_nesting",
            f"You've got {depth} levels of nested loops going.",
            weight=85,
        ))
    elif depth == 2 and not has_lookup:
        out.append(Observation(
            "nested_no_lookup",
            "You're looping inside a loop over the same data, and there's no "
            "lookup structure in there yet.",
            weight=80,
        ))
    elif depth == 2 and has_lookup:
        out.append(Observation(
            "nested_with_lookup",
            "You've reached for a lookup structure, but there's still a loop "
            "inside a loop — so it isn't saving you the scan yet.",
            weight=70,
        ))

    # Several flat passes is a different situation from one nested pair: the
    # cost is linear either way, so the question is whether the passes need to
    # be separate, not whether the work is quadratic.
    if depth == 1 and signals.loops >= 3:
        out.append(Observation(
            "many_flat_passes",
            f"That's {signals.loops} separate passes over the data, none of them nested.",
            weight=50,
        ))
    elif depth == 1 and signals.loops == 2:
        out.append(Observation(
            "two_flat_passes",
            "Two separate passes, one after the other rather than nested.",
            weight=42,
        ))

    if depth >= 1 and len(indexes) >= 2:
        out.append(Observation(
            "multiple_positions",
            f"You're tracking more than one position at once ({', '.join(indexes[:3])}).",
            weight=48,
        ))

    # --- structures ---

    if has_counting:
        out.append(Observation(
            "counting_structure",
            "You're counting occurrences rather than just recording that "
            "something was seen.",
            weight=52,
        ))
    elif has_lookup and depth <= 1:
        out.append(Observation(
            "single_pass_lookup",
            "One pass with a lookup structure — that's the shape people usually "
            "land on here.",
            weight=40,
        ))

    if has_ordered:
        kept = ", ".join(sorted(d for d in signals.data_structures if d.lower() in ORDERED_STRUCTURES))
        out.append(Observation("ordered_structure", f"You're using {kept}.", weight=45))

    if depth >= 1 and not has_lookup and not has_ordered and not signals.has_recursion:
        out.append(Observation(
            "no_auxiliary_structure",
            "You're working straight off the input with nothing kept on the side.",
            weight=38,
        ))

    # --- habits worth naming ---

    if depth >= 2 and not signals.early_exit:
        out.append(Observation(
            "no_early_exit_nested",
            "The nested loops run to completion even once the answer is settled.",
            weight=44,
        ))

    if signals.mutates_iterated_collection:
        out.append(Observation(
            "mutates_iterated",
            "You're changing the same collection you're looping over.",
            weight=88,
        ))
    elif signals.mutation_in_loop:
        out.append(Observation(
            "builds_collection",
            "You're building up a collection as you go rather than computing it in one shot.",
            weight=36,
        ))

    if len(signals.functions) >= 2:
        out.append(Observation(
            "decomposed",
            f"You've split this across {len(signals.functions)} functions rather than "
            "one long body.",
            weight=30,
        ))

    if signals.early_exit:
        out.append(Observation(
            "early_exit",
            "You bail out as soon as you find the answer, which is the right instinct.",
            weight=25,
        ))

    return sorted(out, key=lambda o: -o.weight)


def lead_in(signals: CodeSignals, seen: int = 0) -> str:
    """One sentence about their code to open a hint with.

    `seen` is how many hints this learner has already been given on this
    problem, and it walks down the ranked observations rather than re-serving
    the strongest one every time. Opening four consecutive hints with "There's
    state being mutated inside the loop" makes the whole ladder read as canned,
    which undoes exactly what leading with an observation was for.

    Returns empty once the observations run out. Silence beats repetition — and
    beats a filler observation, which is the same rule the module already
    applied to code it could not parse.
    """
    if not signals.parsed:
        return ""
    ranked = observe(signals)
    return ranked[seen].text if seen < len(ranked) else ""


def suggest_level(signals: CodeSignals, requested: int, hints_used: int) -> tuple[int, str | None]:
    """Adjust the requested rung to match where the learner actually is.

    A ladder that always starts at rung one is the thing that makes hints feel
    canned: being asked "have you considered a lookup structure?" when you have
    already written one reads as not being looked at. Returns the level to serve
    and, when it differs, a short note explaining the jump.
    """
    if not signals.parsed or requested != 1 or hints_used > 0:
        return requested, None

    depth = signals.max_loop_depth
    has_lookup = _has(signals, LOOKUP_STRUCTURES)

    # They already found the structural idea rung 1 and 2 are there to prompt.
    if has_lookup and depth <= 1:
        return 3, "You're already past the first couple of nudges, so here's a later one."
    if signals.has_recursion and signals.has_memoization:
        return 3, "You've already got the memoised recursion going — skipping ahead."
    if depth >= 2 and has_lookup:
        return 2, None

    return requested, None


def compose(nudge: str, signals: CodeSignals, note: str | None = None, seen: int = 0) -> str:
    """Attach the code observation to a card's ladder rung.

    Order matters: the observation goes first so the hint opens with something
    that is unmistakably about their screen, not about the problem in general.
    """
    parts = []
    lead = lead_in(signals, seen)
    if lead:
        parts.append(lead)
    if note:
        parts.append(note)
    parts.append(nudge)
    return " ".join(parts)


def unparsed_note(signals: CodeSignals) -> str:
    """What to say when the code could not be read.

    Said plainly rather than hidden. A learner who is told the analysis is
    generic can weigh it accordingly; one who isn't will assume the mentor read
    their code and drew these conclusions from it, which is worse than useless.
    """
    if signals.parsed:
        return ""
    if signals.error and "unsupported language" in signals.error:
        return ("I couldn't tell which language you're writing in, so this hint is "
                "the general one for this problem rather than one about your code.")
    return ("I couldn't parse what's in the editor yet — this hint is the general "
            "one for this problem rather than one about your code.")


def syntax_help(signals: CodeSignals) -> str | None:
    """A supportive, specific note when the code doesn't compile or parse.

    A learner staring at a syntax error does not need a Socratic nudge about
    hash maps — they need to know the thing is broken and roughly where. Saying
    so is not giving away the answer: a missing colon is not the algorithm, and
    withholding it just makes the tool feel oblivious.

    Tone matters here more than anywhere else in the product. This fires exactly
    when someone is already frustrated, so it names the problem and moves on
    without commentary about their carefulness.
    """
    if signals.parsed or not signals.error:
        return None

    error = signals.error
    if "unsupported language" in error:
        return None  # handled by unparsed_note — not the learner's mistake

    line = ""
    match = _LINE_RE.search(error)
    if match:
        line = f" around line {match.group(1)}"

    detail = error.split(":", 1)[-1].strip() if ":" in error else error
    return (
        f"Before anything else — the code doesn't parse yet{line}. "
        f"The parser says: {detail}. "
        "Worth fixing that first, because nothing else I say will be about what "
        "you actually meant to write."
    )
