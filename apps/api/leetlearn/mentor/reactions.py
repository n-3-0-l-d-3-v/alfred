"""Reaction stamps — the personality layer, replacing the emoji meme library.

Three problems with emoji-and-caption reactions, all of which showed up the
moment a real user looked at one:

  * A 26px emoji beside a caption is the cheapest available signal that
    something was generated rather than written.
  * Meme formats have a shelf life. Anything pinned to a current format is
    dated within months and embarrassing within a year, which is a bad trade
    for a product someone is meant to open daily for a year.
  * The emoji was doing the comedic work, so the writing got lazy.

A reaction is now a short verdict `stamp` set in mono caps plus one `line` of
actual writing. The humour lives in the sentence, which is the only part that
ages well. `tone` maps to a colour the panel already uses for verdicts, so a
reaction looks like part of the review rather than a sticker on top of it.

Intensity remains state-aware, and struggle still overrides the user's setting:
a roast after a clean first-try solve lands, and the identical roast after four
failed submissions is just cruelty with a countdown timer on the user's account.
"""

from __future__ import annotations

from pydantic import BaseModel


class Reaction(BaseModel):
    situation: str
    intensity: str  # gentle | medium | spicy
    stamp: str      # short, mono, uppercase — rendered as a bordered chip
    line: str       # the actual joke or observation
    tone: str = ""  # good | warn | bad — drives the stamp colour


_LIBRARY: dict[str, dict[str, Reaction]] = {}


def _add(situation: str, intensity: str, stamp: str, line: str, tone: str) -> None:
    _LIBRARY.setdefault(situation, {})[intensity] = Reaction(
        situation=situation, intensity=intensity, stamp=stamp, line=line, tone=tone
    )


# --- nested loops where a lookup structure would do ---
_add("nested_loop_when_hashmap_exists", "gentle", "accepted · o(n²)",
     "It works. It also re-reads the same data on every pass — the fix is one "
     "structure away, and it's worth doing while the problem is still fresh.", "warn")
_add("nested_loop_when_hashmap_exists", "medium", "the long way round",
     "Your inner loop keeps re-discovering things the outer loop already knew. "
     "Give it somewhere to write them down.", "warn")
_add("nested_loop_when_hashmap_exists", "spicy", "quadratic · unrepentant",
     "You searched the whole array again. Every single time. It passed, which is "
     "the most dangerous outcome available.", "warn")

# --- recursion without memoization ---
_add("recursion_no_memo", "gentle", "recomputing",
     "Nice recursion. It just solves the same subproblems repeatedly — one cache "
     "turns the tree back into a line.", "warn")
_add("recursion_no_memo", "medium", "exponential · by accident",
     "The same subproblem is being solved thousands of times over. None of those "
     "calls know the others exist.", "warn")
_add("recursion_no_memo", "spicy", "stack · overflowing",
     "This isn't recursion so much as a sustained attack on your own call stack, "
     "and it's winning.", "bad")

# --- optimal ---
_add("clean_solve", "gentle", "optimal", "Target complexity, no wasted work. That's the whole exercise.", "good")
_add("clean_solve", "medium", "no notes",
     "Hit the target on the first honest attempt. Nothing here to fix, which is "
     "mildly irritating to write about.", "good")
_add("clean_solve", "spicy", "showing off",
     "Optimal, readable, and done. Go find something that actually fights back.", "good")

# --- solved but only after lots of hints ---
_add("hint_heavy_solve", "gentle", "solved · assisted",
     "Took a few nudges, which is exactly what they're for. Next one, sit with it "
     "a minute longer before opening this panel.", "warn")
_add("hint_heavy_solve", "medium", "full ladder",
     "You climbed every rung. It counts — and the rungs get pulled away as your "
     "mastery on this topic goes up.", "warn")
_add("hint_heavy_solve", "spicy", "collaborative effort",
     "Four hints in. At this point the two of us should split the credit.", "warn")

# --- clean, no hints ---
_add("no_hints_solve", "gentle", "unassisted", "Zero hints. Straight through to the interesting part.", "good")
_add("no_hints_solve", "medium", "ladder unused", "Didn't need a single nudge. The panel was decorative today.", "good")
_add("no_hints_solve", "spicy", "0 hints · 0 mercy",
     "Solved cold, no help. Do that four more times and the hint budget becomes "
     "theoretical.", "good")

# --- brute force that passes ---
_add("brute_force_accepted", "gentle", "passed · on constraints",
     "Brute force cleared the judge because n was small. Learn the fast version "
     "now, while you already understand the problem.", "warn")
_add("brute_force_accepted", "medium", "got away with it",
     "Accepted, but the constraints did the heavy lifting. Same code at n = 10⁵ "
     "never finishes.", "warn")
_add("brute_force_accepted", "spicy", "out-waited the judge",
     "You didn't outsmart this one, you outlasted it. The interview version has "
     "bigger inputs and a person watching.", "bad")

# --- mutation-heavy / unclear code ---
_add("mutation_soup", "gentle", "mutable state",
     "Correct, but a lot is changing inside that loop. The bug this causes "
     "arrives during a future edit, not today.", "warn")
_add("mutation_soup", "medium", "three things at once",
     "That loop mutates several things per iteration. Reading it back in a month "
     "is going to be an experience.", "warn")
_add("mutation_soup", "spicy", "side effects · plural",
     "This loop changes more state than it computes. Somewhere in there is the "
     "actual algorithm.", "warn")

# --- couldn't parse ---
_add("unparseable", "gentle", "no code read",
     "I couldn't read your editor, so this review is problem-level only — none of "
     "it is about what you actually wrote.", "bad")
_add("unparseable", "medium", "no code read",
     "Nothing readable came back from the editor, so treat everything below as "
     "general rather than personal.", "bad")
_add("unparseable", "spicy", "no code read",
     "Couldn't get your code out of the page, so I'm reviewing the problem and "
     "pretending it's you.", "bad")


_ORDER = ["gentle", "medium", "spicy"]


def pick(situation: str, tone: str = "encourage", hints_used: int = 0, failed_attempts: int = 0) -> Reaction | None:
    """Choose a reaction, softening automatically when the learner has struggled.

    `tone` is the user's setting ("encourage" | "roast"); struggle always wins
    over the setting, because piling on after a hard session is how you lose
    the user you were trying to be funny for.
    """
    variants = _LIBRARY.get(situation)
    if not variants:
        return None

    if tone != "roast":
        target = "gentle"
    elif hints_used >= 3 or failed_attempts >= 3:
        target = "gentle"   # they had a rough time — ease off
    elif hints_used >= 1 or failed_attempts >= 1:
        target = "medium"
    else:
        target = "spicy"    # clean run: they earned the roast

    for level in _ORDER[: _ORDER.index(target) + 1][::-1]:
        if level in variants:
            return variants[level]
    return next(iter(variants.values()))


def situations() -> list[str]:
    return sorted(_LIBRARY)
