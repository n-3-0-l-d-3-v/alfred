"""Work out which archetype a problem belongs to, from what the page tells us.

The knowledge base covers a few dozen problems by hand. LeetCode has thousands,
and a learner who opens one of the others currently gets a 404 and a dead panel —
which is the single largest hole in the product, because it is invisible until
the moment someone actually uses it on a problem we did not anticipate.

The way out is that the *teaching* for a problem is a property of its pattern,
not of the problem (see `archetypes.py`). So if we can name the pattern, we can
teach the problem without anyone having authored it. Naming the pattern is what
this module does, from three sources, in descending order of trust:

  1. Topic tags. LeetCode's own labels, weighted by how discriminative each one
     is: "union-find" appears on one archetype and settles the question outright,
     "array" appears on nine and settles nothing.
  2. Phrases in the title and statement. Curated per archetype, and deliberately
     the kind of wording that survives paraphrase.
  3. The shape of the learner's code, as a tiebreaker only. It says what they are
     *attempting*, which is evidence about the problem but also, often, about
     their misconception — so it never outvotes the problem's own description.

Confidence is the load-bearing output, not the key. A confidently wrong
archetype teaches the wrong lesson with the full authority of the product, which
is worse than admitting we do not recognise the problem: below `MIN_CONFIDENCE`
the caller is expected to fall back to the pattern-free ladder rather than guess.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from ..analysis import CodeSignals
from . import archetypes
from . import archetype_library  # noqa: F401  — registers the archetypes on import

# Below this, we do not claim to know the pattern. Tuned so that a single weak
# shared tag ("array") cannot on its own select an archetype.
MIN_CONFIDENCE = 0.34

# The score at which evidence stops accumulating usefully: roughly one decisive
# topic tag plus one phrase match. Anything at or above this is as sure as the
# tag data can make us.
STRONG_SCORE = 4.5


@dataclass(frozen=True)
class Inference:
    """The chosen archetype, how sure we are, and what else was close."""

    archetype: str | None
    confidence: float
    runners_up: tuple[tuple[str, float], ...] = ()
    evidence: tuple[str, ...] = ()
    nouns: dict[str, str] = field(default_factory=dict)

    @property
    def confident(self) -> bool:
        return self.archetype is not None and self.confidence >= MIN_CONFIDENCE


# --- phrase evidence ---------------------------------------------------------

# Wording that reliably indicates a pattern. Matched against title + statement,
# lowercased. Kept to phrases that describe the *task*, since a statement will
# happily mention "array" for a problem that is not about arrays at all.
PHRASES: dict[str, tuple[str, ...]] = {
    "hash-lookup": ("add up to", "sum to", "seen before", "appears twice", "duplicate",
                    "anagram", "frequency", "occurs", "count of each"),
    "two-pointers-converging": ("sorted array", "two numbers", "palindrome", "container",
                                "most water", "pair that", "from both ends"),
    "fast-slow-pointers": ("cycle", "middle of the linked list", "nth node from the end",
                           "loop in the list"),
    "sliding-window-variable": ("longest substring", "shortest subarray", "without repeating",
                                "at most k", "contains all", "minimum window"),
    "sliding-window-fixed": ("subarray of size", "window of size", "every k", "of length k"),
    "stack-matching": ("valid parentheses", "brackets", "matching", "well-formed",
                       "closing", "opening"),
    "monotonic-stack": ("next greater", "next smaller", "warmer temperature", "days until",
                        "largest rectangle", "span"),
    "binary-search-sorted": ("sorted", "log n", "rotated", "find the index", "search a"),
    "binary-search-on-answer": ("minimum possible", "maximum possible", "minimize the maximum",
                                "smallest k such", "capacity to ship", "eating speed"),
    "heap-top-k": ("k most", "k largest", "k smallest", "top k", "kth largest", "median"),
    "merge-intervals": ("intervals", "overlap", "merge all", "meeting rooms", "non-overlapping"),
    "linked-list-rewiring": ("reverse the list", "linked list", "reorder the list",
                             "merge two sorted lists", "swap nodes"),
    "tree-dfs": ("binary tree", "root of", "depth", "path from root", "subtree", "leaf"),
    "tree-bfs": ("level order", "level by level", "right side view", "each level",
                 "zigzag", "minimum depth"),
    "bst-property": ("binary search tree", "bst", "in-order", "valid bst",
                     "lowest common ancestor"),
    "graph-traversal": ("islands", "grid", "connected", "adjacent cells", "flood",
                        "reachable", "shortest path in"),
    "topological-sort": ("prerequisite", "course", "ordering", "before", "dependency",
                         "can finish"),
    "union-find": ("connected components", "same group", "union", "redundant connection",
                   "number of provinces"),
    "backtracking": ("all possible", "all combinations", "permutations", "subsets",
                     "generate all", "n-queens", "sudoku"),
    "dp-linear": ("maximum sum", "minimum cost", "ways to", "climb", "rob", "decode",
                  "longest increasing"),
    "dp-grid": ("unique paths", "grid", "minimum path sum", "edit distance",
                "longest common subsequence", "matrix of"),
    "prefix-sum": ("range sum", "subarray sum equals", "running total", "cumulative"),
    "greedy": ("minimum number of", "as few as possible", "jump", "gas station",
               "assign", "schedule"),
    "bit-manipulation": ("without using", "bitwise", "xor", "single number", "bits",
                         "power of two"),
    "trie": ("prefix", "starts with", "word dictionary", "autocomplete", "search word"),
    "matrix-traversal": ("rotate the image", "spiral", "in place", "matrix", "transpose"),
    "index-as-storage": ("without extra space", "o(1) extra", "in-place", "missing number",
                         "first missing positive"),
    "design-composite": ("design a", "implement a", "class", "o(1) time for each",
                         "lru", "get and put"),
    "math-reasoning": ("without converting", "integer overflow", "reverse the digits",
                       "roman", "prime", "gcd"),
}

# Code shapes that lend weight to an archetype. Tiebreakers only — see the module
# docstring for why these must not outvote the problem statement.
SIGNAL_HINTS: dict[str, tuple[str, ...]] = {
    "hash-lookup": ("lookup",),
    "dp-linear": ("memo",),
    "dp-grid": ("memo",),
    "backtracking": ("recursion",),
    "tree-dfs": ("recursion",),
    "graph-traversal": ("recursion", "ordered"),
    "heap-top-k": ("ordered",),
    "monotonic-stack": ("ordered",),
    "stack-matching": ("ordered",),
    "tree-bfs": ("ordered",),
}


def _compile_phrases() -> dict[str, tuple[re.Pattern[str], ...]]:
    """Phrases as word-boundary patterns rather than substrings.

    Substring matching quietly wrecks the scoring: "rob" fires on "problem",
    "bst" on "substring", "before" on "therefore". Every statement contains the
    word "problem", so House Robber's evidence was being awarded to essentially
    every problem on the site.
    """
    # A trailing plural is tolerated: statements say "two linked lists" and
    # "merge all overlapping intervals", and a phrase list written in the
    # singular should not miss those.
    return {
        key: tuple(re.compile(rf"\b{re.escape(p)}(?:e?s)?\b") for p in phrases)
        for key, phrases in PHRASES.items()
    }


def _tag_weights() -> dict[str, float]:
    """How much each topic tag is worth, by how few archetypes claim it.

    Straight inverse document frequency. Without it, "array" — which nine
    archetypes list — would drown out the one tag that actually identifies the
    pattern, and every array problem would infer the same archetype.
    """
    counts: Counter[str] = Counter()
    for a in archetypes.all_archetypes():
        counts.update(a.topics)
    total = len(archetypes.all_archetypes())
    return {tag: math.log(1 + total / n) for tag, n in counts.items()}


# Tags that describe *how a solution happens to be written* rather than what
# kind of problem it is. Inverse frequency rewards them for being rare across
# the library, but rarity is the wrong measure for these: LeetCode tags Add Two
# Numbers "recursion", which is true of an implementation and says nothing about
# the problem — enough, before this, to float Backtracking to second place on a
# linked-list traversal.
WEAK_TAGS = {"recursion", "simulation"}
WEAK_TAG_FACTOR = 0.3

_TAG_WEIGHT = _tag_weights()
_PHRASE_RE = _compile_phrases()


def _tag_weight(tag: str) -> float:
    w = _TAG_WEIGHT.get(tag, 1.0)
    return w * WEAK_TAG_FACTOR if tag in WEAK_TAGS else w

# Tags LeetCode uses that name a pattern we model under a different key.
TAG_ALIASES = {
    "hash-table": "hash-table",
    "depth-first-search": "depth-first-search",
    "breadth-first-search": "breadth-first-search",
    "binary-search": "binary-search",
    "dynamic-programming": "dynamic-programming",
    "union-find": "union-find",
    "monotonic-stack": "monotonic-stack",
    "sliding-window": "sliding-window",
    "two-pointers": "two-pointers",
    "prefix-sum": "prefix-sum",
    "topological-sort": "topological-sort",
    "binary-search-tree": "binary-search-tree",
    "linked-list": "linked-list",
    "bit-manipulation": "bit-manipulation",
    "backtracking": "backtracking",
    "trie": "trie",
    "heap-priority-queue": "heap",
    "queue": "queue",
    "stack": "stack",
    "greedy": "greedy",
    "matrix": "matrix",
    "string": "string",
    "array": "array",
    "tree": "tree",
    "binary-tree": "tree",
    "graph": "graph",
    "math": "math",
    "design": "design",
    "sorting": "sorting",
    "simulation": "simulation",
    "recursion": "recursion",
    "counting": "hash-table",
    "hash-function": "hash-table",
    "shortest-path": "graph",
    "memoization": "dynamic-programming",
    "ordered-set": "sorting",
    "divide-and-conquer": "binary-search",
}


def _normalize_tags(topics) -> list[str]:
    return [TAG_ALIASES.get(t.strip().lower(), t.strip().lower()) for t in (topics or []) if t]


def _signal_facts(signals: CodeSignals | None) -> set[str]:
    if signals is None or not signals.parsed:
        return set()
    from .personalize import LOOKUP_STRUCTURES, ORDERED_STRUCTURES

    ds = {d.lower() for d in signals.data_structures}
    facts = set()
    if ds & LOOKUP_STRUCTURES:
        facts.add("lookup")
    if ds & ORDERED_STRUCTURES:
        facts.add("ordered")
    if signals.has_recursion:
        facts.add("recursion")
    if signals.has_memoization:
        facts.add("memo")
    return facts


def infer(
    title: str | None = None,
    topics=None,
    statement: str | None = None,
    signals: CodeSignals | None = None,
) -> Inference:
    """Score every archetype against what we know, and return the best."""
    tags = set(_normalize_tags(topics))
    text = " ".join(filter(None, (title or "", statement or ""))).lower()
    facts = _signal_facts(signals)

    scored: list[tuple[str, float, list[str]]] = []
    for arch in archetypes.all_archetypes():
        score = 0.0
        why: list[str] = []

        for tag in tags & set(arch.topics):
            w = _tag_weight(tag)
            score += w
            if w >= 2.0:
                why.append(f"tagged {tag}")

        hits = [m.group(0) for m in
                (r.search(text) for r in _PHRASE_RE.get(arch.key, ())) if m]
        if hits:
            # Diminishing returns: three loose phrase matches are not three times
            # the evidence of one, and squaring the count would let a verbose
            # statement outweigh an exact topic tag.
            score += 1.1 * math.sqrt(len(hits))
            why.append(f"wording: {hits[0]!r}")

        overlap = facts & set(SIGNAL_HINTS.get(arch.key, ()))
        if overlap:
            score += 0.4 * len(overlap)

        if score > 0:
            scored.append((arch.key, score, why))

    if not scored:
        return Inference(None, 0.0, nouns=_nouns(text, tags))

    scored.sort(key=lambda r: -r[1])
    best_key, best_score, best_why = scored[0]
    second = scored[1][1] if len(scored) > 1 else 0.0

    # Two independent things have to hold before we claim to know the pattern,
    # and multiplying them means either one failing is enough to back off:
    #
    #   strength   — is there much evidence at all? One weak shared tag is not
    #                grounds to teach a pattern.
    #   separation — is this archetype actually ahead? Course Schedule matches
    #                graph-traversal and topological-sort almost equally, and
    #                that really is ambiguous; picking one at full confidence
    #                would teach a coin flip as fact.
    #
    # Share-of-total was the obvious metric and the wrong one: it fell with the
    # number of also-rans, so a clean win over eight irrelevant archetypes
    # scored lower than a coin flip between two.
    strength = min(1.0, best_score / STRONG_SCORE)
    separation = (best_score - second) / best_score if best_score else 0.0
    confidence = strength * (0.45 + 0.55 * separation)

    return Inference(
        archetype=best_key,
        confidence=round(confidence, 3),
        # Scored relative to the winner, not absolutely: the only question a
        # caller asks of a runner-up is "was this nearly as good?", and a raw
        # score cannot answer that without also knowing the winner's.
        runners_up=tuple((k, round(s / best_score, 2)) for k, s, _ in scored[1:4]),
        evidence=tuple(best_why),
        nouns=_nouns(text, tags),
    )


# --- nouns -------------------------------------------------------------------

# What the archetype templates call the thing being iterated. Getting these
# right is most of what makes a generated card read as though it were written
# about this problem rather than assembled from parts.
_SHAPES: tuple[tuple[str, dict[str, str]], ...] = (
    ("linked-list", {"collection": "the list", "unit": "node"}),
    ("tree", {"collection": "the tree", "unit": "node"}),
    ("binary-search-tree", {"collection": "the tree", "unit": "node"}),
    ("graph", {"collection": "the graph", "unit": "node"}),
    ("matrix", {"collection": "the grid", "unit": "cell"}),
    ("string", {"collection": "the string", "unit": "character"}),
    ("intervals", {"collection": "the intervals", "unit": "interval"}),
    ("array", {"collection": "the array", "unit": "element"}),
)

_DEFAULT_NOUNS = {
    "collection": "the input",
    "unit": "element",
    "goal": "the answer you are asked for",
    "relationship": "the condition the problem states",
    "condition": "the condition the problem states",
    "width": "the required size",
}

_K_RE = re.compile(r"\b(?:size|length|window|exactly|at most)\s+k\b")


def _nouns(text: str, tags: set[str]) -> dict[str, str]:
    """Pick the wording the archetype's templates will be rendered with."""
    nouns = dict(_DEFAULT_NOUNS)

    for tag, words in _SHAPES:
        if tag in tags:
            nouns.update(words)
            break
    else:
        # No structural tag. The statement usually still says what it operates on.
        for tag, words in _SHAPES:
            noun = words["collection"].split()[-1]
            if re.search(rf"\b{noun}s?\b", text):
                nouns.update(words)
                break

    if _K_RE.search(text):
        nouns["width"] = "k"
    return nouns
