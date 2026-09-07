"""Dynamic programming and backtracking.

The DP restatements are careful not to name the state. Defining the state *is*
the problem for these, so a restatement that says "the answer at position i is
the best of the two before it" has already done the work the learner came for.
"""

from __future__ import annotations

from ..mentor.card_builder import Spec

SPECS: list[Spec] = [
    Spec(
        slug="climbing-stairs",
        title="Climbing Stairs",
        difficulty="Easy",
        archetype="dp-linear",
        subs={"collection": "the staircase", "unit": "step", "goal": "the number of ways"},
        understanding=(
            "You are climbing a staircase of n steps, and each move takes you up "
            "either one step or two. Count the distinct sequences of moves that reach "
            "the top exactly."
        ),
        topics=("dynamic-programming", "math"),
        code={
            "Plain recursion":
                "def climbStairs(n):\n"
                "    if n <= 2:\n"
                "        return n\n"
                "    return climbStairs(n - 1) + climbStairs(n - 2)",
            "Tabulation":
                "def climbStairs(n):\n"
                "    ways = [0] * (n + 1)\n"
                "    ways[0], ways[1] = 1, 1\n"
                "    for i in range(2, n + 1):\n"
                "        ways[i] = ways[i - 1] + ways[i - 2]\n"
                "    return ways[n]",
            "Rolling values":
                "def climbStairs(n):\n"
                "    a, b = 1, 1\n"
                "    for _ in range(n - 1):\n"
                "        a, b = b, a + b\n"
                "    return b",
        },
        verified=True,
    ),
    Spec(
        slug="house-robber",
        title="House Robber",
        difficulty="Medium",
        archetype="dp-linear",
        subs={"collection": "the street", "unit": "house", "goal": "the largest total"},
        understanding=(
            "Each house holds some amount of money. Taking from two adjacent houses "
            "triggers an alarm. Work out the most you can take without ever choosing "
            "two neighbours."
        ),
        topics=("array", "dynamic-programming"),
        code={
            "Tabulation":
                "def rob(nums):\n"
                "    if not nums:\n"
                "        return 0\n"
                "    best = [0] * (len(nums) + 1)\n"
                "    best[1] = nums[0]\n"
                "    for i in range(2, len(nums) + 1):\n"
                "        best[i] = max(best[i - 1], best[i - 2] + nums[i - 1])\n"
                "    return best[-1]",
            "Rolling values":
                "def rob(nums):\n"
                "    skip, take = 0, 0\n"
                "    for x in nums:\n"
                "        skip, take = max(skip, take), skip + x\n"
                "    return max(skip, take)",
        },
        extra_rewrites=(
            "Solve the variant where the houses are arranged in a circle.",
        ),
        verified=True,
    ),
    Spec(
        slug="coin-change",
        title="Coin Change",
        difficulty="Medium",
        archetype="dp-linear",
        subs={"collection": "the coin list", "unit": "amount", "goal": "the fewest coins"},
        understanding=(
            "Given coin denominations and a target amount, return the smallest number "
            "of coins that sum to it exactly. Coins may be reused freely. If no "
            "combination works, return -1."
        ),
        topics=("array", "dynamic-programming", "breadth-first-search"),
        code={
            "Tabulation":
                "def coinChange(coins, amount):\n"
                "    fewest = [float('inf')] * (amount + 1)\n"
                "    fewest[0] = 0\n"
                "    for target in range(1, amount + 1):\n"
                "        for coin in coins:\n"
                "            if coin <= target:\n"
                "                fewest[target] = min(fewest[target], fewest[target - coin] + 1)\n"
                "    return -1 if fewest[amount] == float('inf') else fewest[amount]",
        },
        extra_pitfalls=(
            {"mistake": "Taking the largest coin first",
             "why": "greedy fails on denominations that are not well-behaved",
             "symptom": "wrong answers on coin sets like 1, 3 and 4"},
        ),
        extra_edge_cases=("An amount of zero", "An amount no combination can reach"),
        extra_rewrites=(
            "Find an input where the greedy largest-coin-first rule gives the wrong answer.",
        ),
        verified=True,
    ),
    Spec(
        slug="longest-common-subsequence",
        title="Longest Common Subsequence",
        difficulty="Medium",
        archetype="dp-grid",
        subs={"collection": "the two strings", "unit": "character", "goal": "the longest shared run"},
        understanding=(
            "Return the length of the longest sequence of characters appearing in both "
            "strings in the same relative order. The characters need not be adjacent — "
            "only their order matters."
        ),
        topics=("string", "dynamic-programming"),
        code={
            "Full table":
                "def longestCommonSubsequence(a, b):\n"
                "    table = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]\n"
                "    for i in range(1, len(a) + 1):\n"
                "        for j in range(1, len(b) + 1):\n"
                "            if a[i - 1] == b[j - 1]:\n"
                "                table[i][j] = table[i - 1][j - 1] + 1\n"
                "            else:\n"
                "                table[i][j] = max(table[i - 1][j], table[i][j - 1])\n"
                "    return table[-1][-1]",
        },
        extra_rewrites=(
            "Reduce the table to two rows and explain why the diagonal value must be "
            "saved before it is overwritten.",
        ),
        verified=True,
    ),
    Spec(
        slug="subsets",
        title="Subsets",
        difficulty="Medium",
        archetype="backtracking",
        subs={"collection": "the array", "unit": "number", "goal": "every subset"},
        understanding=(
            "Given a list of distinct numbers, produce every possible subset, "
            "including the empty one and the whole list. Order within a subset does "
            "not matter, and no subset may repeat."
        ),
        topics=("array", "backtracking", "bit-manipulation"),
        code={
            "Backtracking with pruning":
                "def subsets(nums):\n"
                "    out = []\n"
                "    current = []\n\n"
                "    def explore(start):\n"
                "        out.append(current[:])\n"
                "        for i in range(start, len(nums)):\n"
                "            current.append(nums[i])\n"
                "            explore(i + 1)\n"
                "            current.pop()\n\n"
                "    explore(0)\n"
                "    return out",
        },
        extra_rewrites=(
            "Generate the subsets from the bits of the numbers 0 to 2^n - 1 instead.",
            "Handle duplicate inputs without producing duplicate subsets.",
        ),
        verified=True,
    ),
    Spec(
        slug="combination-sum",
        title="Combination Sum",
        difficulty="Medium",
        archetype="backtracking",
        subs={"collection": "the candidate list", "unit": "number", "goal": "every combination"},
        understanding=(
            "Given distinct candidate numbers and a target, find every combination "
            "that sums to the target. A candidate may be reused any number of times, "
            "and two combinations differing only in order count as the same one."
        ),
        topics=("array", "backtracking"),
        code={
            "Backtracking with pruning":
                "def combinationSum(candidates, target):\n"
                "    out = []\n"
                "    current = []\n\n"
                "    def explore(start, remaining):\n"
                "        if remaining == 0:\n"
                "            out.append(current[:])\n"
                "            return\n"
                "        for i in range(start, len(candidates)):\n"
                "            if candidates[i] > remaining:\n"
                "                continue\n"
                "            current.append(candidates[i])\n"
                "            explore(i, remaining - candidates[i])\n"
                "            current.pop()\n\n"
                "    explore(0, target)\n"
                "    return out",
        },
        extra_pitfalls=(
            {"mistake": "Recursing from the next index when reuse is allowed",
             "why": "it forbids repeating a candidate the problem permits",
             "symptom": "missing every combination that uses one number twice"},
        ),
        verified=True,
    ),
]
