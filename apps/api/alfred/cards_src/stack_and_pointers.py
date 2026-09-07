"""Stacks, two pointers, and binary search."""

from __future__ import annotations

from ..mentor.card_builder import Spec

SPECS: list[Spec] = [
    Spec(
        slug="two-sum-ii-input-array-is-sorted",
        title="Two Sum II — Input Array Is Sorted",
        difficulty="Medium",
        archetype="two-pointers-converging",
        subs={
            "collection": "the sorted array",
            "unit": "number",
            "goal": "the pair summing to the target",
        },
        understanding=(
            "Same as Two Sum, with one extra guarantee: the array is already sorted "
            "in ascending order. Exactly one pair works, and the answer is their "
            "positions using 1-based indexing."
        ),
        topics=("array", "two-pointers", "binary-search"),
        code={
            "Brute force (all pairs)":
                "def twoSum(numbers, target):\n"
                "    for i in range(len(numbers)):\n"
                "        for j in range(i + 1, len(numbers)):\n"
                "            if numbers[i] + numbers[j] == target:\n"
                "                return [i + 1, j + 1]",
            "Converging pointers":
                "def twoSum(numbers, target):\n"
                "    lo, hi = 0, len(numbers) - 1\n"
                "    while lo < hi:\n"
                "        total = numbers[lo] + numbers[hi]\n"
                "        if total == target:\n"
                "            return [lo + 1, hi + 1]\n"
                "        if total < target:\n"
                "            lo += 1\n"
                "        else:\n"
                "            hi -= 1",
        },
        extra_pitfalls=(
            {"mistake": "Returning 0-based positions",
             "why": "this variant asks for 1-based indices",
             "symptom": "every answer off by one in both positions"},
        ),
        verified=True,
    ),
    Spec(
        slug="container-with-most-water",
        title="Container With Most Water",
        difficulty="Medium",
        archetype="two-pointers-converging",
        subs={
            "collection": "the height list",
            "unit": "line",
            "goal": "the largest area",
        },
        understanding=(
            "Each number is the height of a vertical line. Pick two lines; together "
            "with the ground they form a container. Report the most water any pair "
            "can hold — width is the distance between them, height is the shorter one."
        ),
        topics=("array", "two-pointers", "greedy"),
        code={
            "Brute force (all pairs)":
                "def maxArea(height):\n"
                "    best = 0\n"
                "    for i in range(len(height)):\n"
                "        for j in range(i + 1, len(height)):\n"
                "            best = max(best, (j - i) * min(height[i], height[j]))\n"
                "    return best",
            "Converging pointers":
                "def maxArea(height):\n"
                "    lo, hi = 0, len(height) - 1\n"
                "    best = 0\n"
                "    while lo < hi:\n"
                "        best = max(best, (hi - lo) * min(height[lo], height[hi]))\n"
                "        if height[lo] < height[hi]:\n"
                "            lo += 1\n"
                "        else:\n"
                "            hi -= 1\n"
                "    return best",
        },
        extra_rewrites=(
            "Prove that moving the taller line inward can never find a better area.",
        ),
        verified=True,
    ),
    Spec(
        slug="min-stack",
        title="Min Stack",
        difficulty="Medium",
        archetype="design-composite",
        subs={
            "collection": "the stack",
            "unit": "value",
            "goal": "the minimum",
        },
        understanding=(
            "Build a stack supporting push, pop, top, and retrieving the smallest "
            "value currently held — all of them in constant time. The minimum has to "
            "stay correct as values are popped."
        ),
        topics=("stack", "design"),
        code={
            "Single structure":
                "class MinStack:\n"
                "    def __init__(self):\n"
                "        self.items = []\n\n"
                "    def push(self, val):\n"
                "        self.items.append(val)\n\n"
                "    def pop(self):\n"
                "        self.items.pop()\n\n"
                "    def top(self):\n"
                "        return self.items[-1]\n\n"
                "    def getMin(self):\n"
                "        return min(self.items)",
            "Two structures kept in step":
                "class MinStack:\n"
                "    def __init__(self):\n"
                "        self.items = []\n"
                "        self.mins = []\n\n"
                "    def push(self, val):\n"
                "        self.items.append(val)\n"
                "        self.mins.append(val if not self.mins else min(val, self.mins[-1]))\n\n"
                "    def pop(self):\n"
                "        self.items.pop()\n"
                "        self.mins.pop()\n\n"
                "    def top(self):\n"
                "        return self.items[-1]\n\n"
                "    def getMin(self):\n"
                "        return self.mins[-1]",
        },
        extra_pitfalls=(
            {"mistake": "Storing each new minimum only when it changes",
             "why": "popping then has to work out whether the minimum moved",
             "symptom": "a stale minimum after popping the smallest value"},
        ),
        verified=True,
    ),
    Spec(
        slug="binary-search",
        title="Binary Search",
        difficulty="Easy",
        archetype="binary-search-sorted",
        subs={
            "collection": "the array",
            "unit": "number",
            "goal": "the target value",
        },
        understanding=(
            "A sorted array and a target. Return the position of the target, or -1 if "
            "it isn't there. It has to run in logarithmic time, which rules out "
            "looking at everything."
        ),
        topics=("array", "binary-search"),
        code={
            "Linear scan":
                "def search(nums, target):\n"
                "    for i, x in enumerate(nums):\n"
                "        if x == target:\n"
                "            return i\n"
                "    return -1",
            "Binary search":
                "def search(nums, target):\n"
                "    lo, hi = 0, len(nums) - 1\n"
                "    while lo <= hi:\n"
                "        mid = (lo + hi) // 2\n"
                "        if nums[mid] == target:\n"
                "            return mid\n"
                "        if nums[mid] < target:\n"
                "            lo = mid + 1\n"
                "        else:\n"
                "            hi = mid - 1\n"
                "    return -1",
        },
        verified=True,
    ),
    Spec(
        slug="reverse-linked-list",
        title="Reverse Linked List",
        difficulty="Easy",
        archetype="linked-list-rewiring",
        subs={
            "collection": "the list",
            "unit": "node",
            "goal": "the reversed list",
        },
        understanding=(
            "Given the head of a singly linked list, return the head of the same list "
            "with every link pointing the other way. You can only walk forwards, one "
            "node at a time."
        ),
        topics=("linked-list", "recursion"),
        code={
            "Copy into an array":
                "def reverseList(head):\n"
                "    values = []\n"
                "    node = head\n"
                "    while node:\n"
                "        values.append(node.val)\n"
                "        node = node.next\n"
                "    node = head\n"
                "    for v in reversed(values):\n"
                "        node.val = v\n"
                "        node = node.next\n"
                "    return head",
            "In-place rewiring":
                "def reverseList(head):\n"
                "    prev = None\n"
                "    node = head\n"
                "    while node:\n"
                "        nxt = node.next\n"
                "        node.next = prev\n"
                "        prev = node\n"
                "        node = nxt\n"
                "    return prev",
        },
        verified=True,
    ),
]
