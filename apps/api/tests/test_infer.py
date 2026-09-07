"""Archetype inference: does it pick the right pattern, and does it know when
it can't?

The second half matters more than the first. A wrong archetype served at full
confidence teaches the wrong lesson in the product's own voice, which is worse
for a learner than being told we don't recognise the problem — so the tests that
assert *low* confidence are the load-bearing ones here.
"""

from __future__ import annotations

import pytest

from alfred.mentor.infer import MIN_CONFIDENCE, infer

# (title, topic tags, statement fragment, expected archetype)
KNOWN = [
    ("1. Two Sum", ["array", "hash-table"],
     "return indices of the two numbers such that they add up to target",
     "hash-lookup"),
    ("2. Add Two Numbers", ["linked-list", "math", "recursion"],
     "two non-empty linked lists representing two non-negative integers, digits stored in reverse order",
     "linked-list-rewiring"),
    ("3. Longest Substring Without Repeating Characters", ["hash-table", "string", "sliding-window"],
     "find the length of the longest substring without repeating characters",
     "sliding-window-variable"),
    ("42. Trapping Rain Water", ["array", "two-pointers", "dynamic-programming", "stack", "monotonic-stack"],
     "elevation map, compute how much water it can trap",
     "monotonic-stack"),
    ("70. Climbing Stairs", ["math", "dynamic-programming", "memoization"],
     "you are climbing a staircase, it takes n steps, in how many distinct ways can you climb",
     "dp-linear"),
    ("104. Maximum Depth of Binary Tree", ["tree", "depth-first-search", "binary-tree"],
     "given the root of a binary tree, return its maximum depth",
     "tree-dfs"),
    ("146. LRU Cache", ["hash-table", "linked-list", "design", "doubly-linked-list"],
     "design a data structure, LRU cache, get and put in O(1) average time complexity",
     "design-composite"),
    ("200. Number of Islands", ["array", "depth-first-search", "breadth-first-search", "matrix"],
     "grid of 1s land and 0s water, return the number of islands",
     "graph-traversal"),
    ("208. Implement Trie", ["hash-table", "string", "design", "trie"],
     "implement a trie with insert, search, and starts with prefix",
     "trie"),
    ("56. Merge Intervals", ["array", "sorting", "intervals"],
     "merge all overlapping intervals and return non-overlapping intervals",
     "merge-intervals"),
]


@pytest.mark.parametrize("title,topics,statement,expected", KNOWN)
def test_picks_the_right_archetype(title, topics, statement, expected):
    got = infer(title, topics, statement)
    assert got.archetype == expected, f"{title}: got {got.archetype} ({got.confidence})"
    assert got.confident, f"{title}: correct pick but not confident ({got.confidence})"


def test_no_signal_at_all_infers_nothing():
    """An empty page must not produce a pattern. There is nothing to infer from,
    and a default archetype would be a guess dressed as a diagnosis."""
    got = infer(None, [], None)
    assert got.archetype is None
    assert not got.confident


def test_a_single_weak_tag_is_not_enough():
    """'array' is on nine archetypes. On its own it identifies nothing, and the
    inverse-frequency weighting exists precisely so it cannot win."""
    got = infer("Some Problem", ["array"], "given an array of integers")
    assert not got.confident, f"a bare 'array' tag reached {got.confidence}"


def test_genuinely_ambiguous_problems_report_low_confidence():
    """Is Subsequence is a forward two-pointer scan over two sequences, which no
    archetype in the library models. Its tags pull three ways at once, and the
    honest output is a low score rather than whichever one edges ahead."""
    got = infer(
        "392. Is Subsequence",
        ["two-pointers", "string", "dynamic-programming"],
        "given two strings s and t, return true if s is a subsequence of t",
    )
    assert not got.confident, f"claimed {got.archetype} at {got.confidence}"


def test_confidence_falls_when_two_archetypes_tie():
    """Course Schedule is legitimately both a traversal and a topological sort.
    It should still infer something, but visibly less surely than Two Sum."""
    tie = infer("207. Course Schedule",
                ["depth-first-search", "breadth-first-search", "graph", "topological-sort"],
                "prerequisites, return true if you can finish all courses")
    clear = infer("1. Two Sum", ["array", "hash-table"],
                  "return indices of the two numbers such that they add up to target")
    assert tie.archetype in {"graph-traversal", "topological-sort"}
    assert tie.confidence < clear.confidence


def test_confidence_is_a_probability_like_number():
    for title, topics, statement, _ in KNOWN:
        got = infer(title, topics, statement)
        assert 0.0 <= got.confidence <= 1.0


def test_nouns_follow_the_data_shape():
    tree = infer("104. Maximum Depth", ["tree", "binary-tree"], "root of a binary tree")
    assert tree.nouns["unit"] == "node"
    text = infer("5. Longest Palindrome", ["string"], "given a string s return the longest palindromic substring")
    assert text.nouns["unit"] == "character"


def test_code_signals_never_outvote_the_statement():
    """Someone brute-forcing Two Sum with nested loops and no hash map must still
    be taught the hash-lookup pattern. Their code is evidence about where they
    are stuck, not about what the problem is."""
    from alfred.analysis import analyze

    brute = analyze("python", "def f(n,t):\n    for i in range(len(n)):\n        for j in range(i+1,len(n)):\n            if n[i]+n[j]==t: return [i,j]\n")
    got = infer("1. Two Sum", ["array", "hash-table"],
                "return indices of the two numbers such that they add up to target",
                signals=brute)
    assert got.archetype == "hash-lookup"


def test_min_confidence_is_actually_enforced_by_confident():
    from dataclasses import replace

    got = infer("1. Two Sum", ["array", "hash-table"], "add up to target")
    assert replace(got, confidence=MIN_CONFIDENCE - 0.01).confident is False
    assert replace(got, confidence=MIN_CONFIDENCE).confident is True
