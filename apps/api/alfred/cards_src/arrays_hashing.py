"""Arrays & hashing — problems whose insight is "remember what you've seen".

The `understanding` field is written per problem and is the one thing no
archetype can supply. It restates the task in plain language *without* hinting
at an approach, because it is shown pre-AC: saying "you need to count
occurrences" on Valid Anagram would hand over the entire problem.
"""

from __future__ import annotations

from ..mentor.card_builder import Spec

SPECS: list[Spec] = [
    Spec(
        slug="contains-duplicate",
        title="Contains Duplicate",
        difficulty="Easy",
        archetype="hash-lookup",
        subs={
            "collection": "the array",
            "unit": "number",
            "goal": "a repeat",
            "relationship": "whether this number has appeared before",
        },
        understanding=(
            "You're given a list of numbers. Say whether any value shows up more "
            "than once. You don't need to say which value, or where — just whether "
            "it happens at all."
        ),
        topics=("array", "hash-table", "sorting"),
        extra_patterns=(("Sorting first", 0.35),),
        code={
            "Brute force (compare every pair)":
                "def containsDuplicate(nums):\n"
                "    for i in range(len(nums)):\n"
                "        for j in range(i + 1, len(nums)):\n"
                "            if nums[i] == nums[j]:\n"
                "                return True\n"
                "    return False",
            "One-pass hash map":
                "def containsDuplicate(nums):\n"
                "    seen = set()\n"
                "    for x in nums:\n"
                "        if x in seen:\n"
                "            return True\n"
                "        seen.add(x)\n"
                "    return False",
        },
        extra_rewrites=(
            "Solve it in O(1) extra space and say what you gave up to get there.",
            "Return the first repeated value rather than a yes or no.",
        ),
        verified=True,
    ),
    Spec(
        slug="valid-anagram",
        title="Valid Anagram",
        difficulty="Easy",
        archetype="hash-lookup",
        subs={
            "collection": "the two strings",
            "unit": "character",
            "goal": "a matching rearrangement",
            "relationship": "whether both strings use each character the same number of times",
        },
        understanding=(
            "Two strings. Decide whether one is a rearrangement of the other — same "
            "characters, same quantities, order irrelevant. Different lengths can "
            "never qualify."
        ),
        topics=("string", "hash-table", "sorting"),
        extra_patterns=(("Sorting both and comparing", 0.45),),
        code={
            "Brute force (compare every pair)":
                "def isAnagram(s, t):\n"
                "    if len(s) != len(t):\n"
                "        return False\n"
                "    return sorted(s) == sorted(t)",
            "One-pass hash map":
                "def isAnagram(s, t):\n"
                "    if len(s) != len(t):\n"
                "        return False\n"
                "    counts = {}\n"
                "    for c in s:\n"
                "        counts[c] = counts.get(c, 0) + 1\n"
                "    for c in t:\n"
                "        if counts.get(c, 0) == 0:\n"
                "            return False\n"
                "        counts[c] -= 1\n"
                "    return True",
        },
        extra_edge_cases=(
            "Strings of different lengths",
            "Unicode beyond the 26 lowercase letters",
        ),
        extra_rewrites=(
            "Handle Unicode input rather than assuming 26 lowercase letters.",
            "Solve it without extra space, and state the cost.",
        ),
        verified=True,
    ),
    Spec(
        slug="group-anagrams",
        title="Group Anagrams",
        difficulty="Medium",
        archetype="hash-lookup",
        subs={
            "collection": "the list of strings",
            "unit": "string",
            "goal": "the groups",
            "relationship": "whether two strings are rearrangements of each other",
        },
        understanding=(
            "Given a list of strings, gather them into groups where everything in a "
            "group is a rearrangement of everything else in it. Any group order is "
            "fine, and any order within a group."
        ),
        topics=("array", "string", "hash-table", "sorting"),
        code={
            "Brute force (compare every pair)":
                "def groupAnagrams(strs):\n"
                "    groups = []\n"
                "    for s in strs:\n"
                "        for g in groups:\n"
                "            if sorted(g[0]) == sorted(s):\n"
                "                g.append(s)\n"
                "                break\n"
                "        else:\n"
                "            groups.append([s])\n"
                "    return groups",
            "One-pass hash map":
                "def groupAnagrams(strs):\n"
                "    groups = {}\n"
                "    for s in strs:\n"
                "        key = tuple(sorted(s))\n"
                "        groups.setdefault(key, []).append(s)\n"
                "    return list(groups.values())",
        },
        extra_pitfalls=(
            {"mistake": "Using a mutable value as a dictionary key",
             "why": "lists cannot be hashed, so the key has to be a tuple or a string",
             "symptom": "a TypeError about unhashable types"},
        ),
        extra_rewrites=(
            "Build the key from character counts instead of sorting, and compare the complexities.",
        ),
        verified=True,
    ),
    Spec(
        slug="top-k-frequent-elements",
        title="Top K Frequent Elements",
        difficulty="Medium",
        archetype="heap-top-k",
        subs={
            "collection": "the array",
            "unit": "value",
            "goal": "the most frequent values",
            "width": "k",
        },
        understanding=(
            "Given a list of numbers and a number k, return the k values that appear "
            "most often. The answer is guaranteed to be unique, and you can return "
            "them in any order."
        ),
        topics=("array", "hash-table", "heap", "counting"),
        code={
            "Sort everything":
                "def topKFrequent(nums, k):\n"
                "    counts = {}\n"
                "    for x in nums:\n"
                "        counts[x] = counts.get(x, 0) + 1\n"
                "    return sorted(counts, key=counts.get, reverse=True)[:k]",
            "Bounded heap":
                "import heapq\n\n"
                "def topKFrequent(nums, k):\n"
                "    counts = {}\n"
                "    for x in nums:\n"
                "        counts[x] = counts.get(x, 0) + 1\n"
                "    heap = []\n"
                "    for value, freq in counts.items():\n"
                "        heapq.heappush(heap, (freq, value))\n"
                "        if len(heap) > k:\n"
                "            heapq.heappop(heap)\n"
                "    return [value for freq, value in heap]",
        },
        extra_rewrites=(
            "Solve it in O(n) with bucket sort, and explain why the buckets are bounded.",
        ),
        verified=True,
    ),
    Spec(
        slug="product-of-array-except-self",
        title="Product of Array Except Self",
        difficulty="Medium",
        archetype="prefix-sum",
        subs={
            "collection": "the array",
            "unit": "number",
            "goal": "each position's product",
        },
        understanding=(
            "For every position, produce the product of every other number in the "
            "array. Division is not allowed, and the whole thing has to run in linear "
            "time."
        ),
        topics=("array", "prefix-sum"),
        code={
            "Re-sum each range":
                "def productExceptSelf(nums):\n"
                "    out = []\n"
                "    for i in range(len(nums)):\n"
                "        p = 1\n"
                "        for j in range(len(nums)):\n"
                "            if i != j:\n"
                "                p *= nums[j]\n"
                "        out.append(p)\n"
                "    return out",
            "Prefix totals":
                "def productExceptSelf(nums):\n"
                "    n = len(nums)\n"
                "    out = [1] * n\n"
                "    running = 1\n"
                "    for i in range(n):\n"
                "        out[i] = running\n"
                "        running *= nums[i]\n"
                "    running = 1\n"
                "    for i in range(n - 1, -1, -1):\n"
                "        out[i] *= running\n"
                "        running *= nums[i]\n"
                "    return out",
        },
        extra_edge_cases=(
            "A single zero in the array",
            "Two or more zeroes",
        ),
        extra_pitfalls=(
            {"mistake": "Reaching for division",
             "why": "the problem forbids it, and it breaks on zeroes anyway",
             "symptom": "a division-by-zero, or a rejected solution"},
        ),
        verified=True,
    ),
]
