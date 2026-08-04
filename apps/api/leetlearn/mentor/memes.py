"""Curated meme response library.

Deliberately NOT LLM-generated at runtime: generated memes are expensive, slow,
brand-unsafe, and reliably unfunny. Instead we pick a `(situation, intensity)`
from a hand-written library.

Intensity is state-aware — see `pick()`. A roast lands after a clean first-try
solve; the same roast after four failed submissions reads as cruel and churns
the user. Under struggle we always soften, regardless of the user's tone setting.

`asset` is a path under the extension's `assets/memes/` for a future image drop.
Until those exist the `emoji` + `caption` render fine on their own.
"""

from __future__ import annotations

from pydantic import BaseModel


class Meme(BaseModel):
    situation: str
    intensity: str  # gentle | medium | spicy
    emoji: str
    caption: str
    asset: str | None = None


_LIBRARY: dict[str, dict[str, Meme]] = {}


def _add(situation: str, intensity: str, emoji: str, caption: str) -> None:
    _LIBRARY.setdefault(situation, {})[intensity] = Meme(
        situation=situation, intensity=intensity, emoji=emoji, caption=caption,
        asset=f"assets/memes/{situation}_{intensity}.png",
    )


# --- nested loops where a hash map would do ---
_add("nested_loop_when_hashmap_exists", "gentle", "🐌",
     "Two loops walked so a hash map could run. It works — now let it fly.")
_add("nested_loop_when_hashmap_exists", "medium", "🔁",
     "Your inner loop is re-reading the same array like it forgot everything. It did. Give it a memory.")
_add("nested_loop_when_hashmap_exists", "spicy", "💀",
     "O(n²) on an array problem in 2026. Somewhere, a hash map is crying.")

# --- recursion without memoization ---
_add("recursion_no_memo", "gentle", "🌱",
     "Lovely recursion. It just solves the same subproblem a few thousand times — cache it.")
_add("recursion_no_memo", "medium", "🌀",
     "fib(40) called fib(2) about 63 million times. They've met. Introduce a memo.")
_add("recursion_no_memo", "spicy", "🔥",
     "This isn't recursion, it's a denial-of-service attack on your own call stack.")

# --- optimal ---
_add("clean_solve", "gentle", "✨", "Optimal complexity, no wasted work. That's the good stuff.")
_add("clean_solve", "medium", "🎯", "Hit the target complexity first try. Nothing to fix. Annoying, honestly.")
_add("clean_solve", "spicy", "🗿", "No notes. Genuinely. Go do a Hard one.")

# --- solved but only after lots of hints ---
_add("hint_heavy_solve", "gentle", "🧗",
     "Took a few hints — that's what they're for. Next one, try going a level lower before you ask.")
_add("hint_heavy_solve", "medium", "🪜",
     "You climbed the whole hint ladder. It counts! But the rungs get taken away as you improve.")
_add("hint_heavy_solve", "spicy", "🧾",
     "Solved with four hints. We're calling that a collaboration.")

# --- clean, no hints ---
_add("no_hints_solve", "gentle", "🎖️", "Solved with zero hints. Straight to the good part.")
_add("no_hints_solve", "medium", "🥇", "No hints needed. The ladder stays folded.")
_add("no_hints_solve", "spicy", "😤", "Didn't touch a single hint. Show-off. Keep it up.")

# --- brute force that passes ---
_add("brute_force_accepted", "gentle", "🧱",
     "Brute force passed — the constraints were kind. Learn the fast way before they aren't.")
_add("brute_force_accepted", "medium", "🎲",
     "Accepted, but you got lucky on constraints. That same code times out at n = 10⁵.")
_add("brute_force_accepted", "spicy", "🃏",
     "You didn't solve it, you out-waited it. The judge blinked first.")

# --- mutation-heavy / unclear code ---
_add("mutation_soup", "gentle", "🥄",
     "Lots of in-place mutation in that loop — correct, but hard to reason about later.")
_add("mutation_soup", "medium", "🍲",
     "That loop mutates three things at once. Future-you will read this and file a bug.")
_add("mutation_soup", "spicy", "☠️",
     "This loop has more side effects than a pharmaceutical ad.")

# --- couldn't parse ---
_add("unparseable", "gentle", "🔍",
     "Couldn't parse this one, so the review is card-based only. Complexity notes still apply.")
_add("unparseable", "medium", "🔍", "Parser tapped out. Review is card-based for now.")
_add("unparseable", "spicy", "🔍", "Even the parser gave up. That's a first.")


_ORDER = ["gentle", "medium", "spicy"]


def pick(situation: str, tone: str = "encourage", hints_used: int = 0, failed_attempts: int = 0) -> Meme | None:
    """Choose a meme, softening automatically when the learner has struggled.

    `tone` is the user's setting ("encourage" | "roast"); struggle always wins
    over the setting, because piling on after a hard session is how you lose users.
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

    # fall back down the intensity ladder if that variant doesn't exist
    for level in _ORDER[: _ORDER.index(target) + 1][::-1]:
        if level in variants:
            return variants[level]
    return next(iter(variants.values()))


def situations() -> list[str]:
    return sorted(_LIBRARY)
