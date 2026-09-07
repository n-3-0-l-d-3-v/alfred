"""Sliding window — problems whose answer is a contiguous stretch."""

from __future__ import annotations

from ..mentor.card_builder import Spec

SPECS: list[Spec] = [
    Spec(
        slug="best-time-to-buy-and-sell-stock",
        title="Best Time to Buy and Sell Stock",
        difficulty="Easy",
        archetype="sliding-window-variable",
        subs={
            "collection": "the price list",
            "unit": "day",
            "goal": "the best profit",
            "condition": "the buy day comes before the sell day",
        },
        understanding=(
            "A list of daily prices. Pick one day to buy and a later day to sell, and "
            "report the largest profit available. If every choice loses money, the "
            "answer is zero — you're allowed to do nothing."
        ),
        topics=("array", "dynamic-programming"),
        code={
            "Check every stretch":
                "def maxProfit(prices):\n"
                "    best = 0\n"
                "    for i in range(len(prices)):\n"
                "        for j in range(i + 1, len(prices)):\n"
                "            best = max(best, prices[j] - prices[i])\n"
                "    return best",
            "Sliding window":
                "def maxProfit(prices):\n"
                "    cheapest = float('inf')\n"
                "    best = 0\n"
                "    for p in prices:\n"
                "        cheapest = min(cheapest, p)\n"
                "        best = max(best, p - cheapest)\n"
                "    return best",
        },
        extra_edge_cases=(
            "Prices that only ever fall",
            "A single day",
        ),
        extra_pitfalls=(
            {"mistake": "Allowing the sell day to precede the buy day",
             "why": "the profit must come from a later day",
             "symptom": "an impossible profit on a falling market"},
        ),
        verified=True,
    ),
    Spec(
        slug="longest-substring-without-repeating-characters",
        title="Longest Substring Without Repeating Characters",
        difficulty="Medium",
        archetype="sliding-window-variable",
        subs={
            "collection": "the string",
            "unit": "character",
            "goal": "the longest stretch",
            "condition": "no character repeats inside the stretch",
        },
        understanding=(
            "Find the length of the longest run of consecutive characters that "
            "contains no duplicates. Contiguous matters — you cannot skip characters "
            "and stitch the rest together."
        ),
        topics=("string", "sliding-window", "hash-table"),
        code={
            "Check every stretch":
                "def lengthOfLongestSubstring(s):\n"
                "    best = 0\n"
                "    for i in range(len(s)):\n"
                "        seen = set()\n"
                "        for j in range(i, len(s)):\n"
                "            if s[j] in seen:\n"
                "                break\n"
                "            seen.add(s[j])\n"
                "            best = max(best, j - i + 1)\n"
                "    return best",
            "Sliding window":
                "def lengthOfLongestSubstring(s):\n"
                "    last = {}\n"
                "    start = 0\n"
                "    best = 0\n"
                "    for i, c in enumerate(s):\n"
                "        if c in last and last[c] >= start:\n"
                "            start = last[c] + 1\n"
                "        last[c] = i\n"
                "        best = max(best, i - start + 1)\n"
                "    return best",
        },
        extra_pitfalls=(
            {"mistake": "Moving the left boundary backwards",
             "why": "a remembered position may be from before the current window",
             "symptom": "lengths larger than the string on inputs with repeats"},
        ),
        verified=True,
    ),
    Spec(
        slug="longest-repeating-character-replacement",
        title="Longest Repeating Character Replacement",
        difficulty="Medium",
        archetype="sliding-window-variable",
        subs={
            "collection": "the string",
            "unit": "character",
            "goal": "the longest stretch",
            "condition": "at most k characters differ from the most common one",
        },
        understanding=(
            "You may change up to k characters to anything you like. Find the longest "
            "run you can make entirely of one repeated character. The run must be "
            "contiguous."
        ),
        topics=("string", "sliding-window", "hash-table"),
        code={
            "Check every stretch":
                "def characterReplacement(s, k):\n"
                "    best = 0\n"
                "    for i in range(len(s)):\n"
                "        counts = {}\n"
                "        for j in range(i, len(s)):\n"
                "            counts[s[j]] = counts.get(s[j], 0) + 1\n"
                "            width = j - i + 1\n"
                "            if width - max(counts.values()) <= k:\n"
                "                best = max(best, width)\n"
                "    return best",
            "Sliding window":
                "def characterReplacement(s, k):\n"
                "    counts = {}\n"
                "    start = 0\n"
                "    best = 0\n"
                "    most = 0\n"
                "    for i, c in enumerate(s):\n"
                "        counts[c] = counts.get(c, 0) + 1\n"
                "        most = max(most, counts[c])\n"
                "        while (i - start + 1) - most > k:\n"
                "            counts[s[start]] -= 1\n"
                "            start += 1\n"
                "        best = max(best, i - start + 1)\n"
                "    return best",
        },
        extra_rewrites=(
            "Explain why the count of the most common character never needs to be "
            "recomputed downward, or find the input where that reasoning fails.",
        ),
        verified=True,
    ),
]
