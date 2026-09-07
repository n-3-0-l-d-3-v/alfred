import pytest

from alfred.analysis import analyze
from alfred.mentor.contracts import looks_like_code


def test_simple_loop():
    sig = analyze("python", "x = 10\nfor i in range(x):\n    print(i)")
    assert sig.parsed
    assert sig.loops == 1
    assert sig.max_loop_depth == 1
    assert "x" in sig.variables and "i" in sig.variables


def test_nested_loops_estimate_quadratic():
    code = "for i in range(5):\n    for j in range(5):\n        x = i * j"
    sig = analyze("python", code)
    assert sig.max_loop_depth == 2
    assert "nested loops" in sig.patterns
    assert sig.estimated_time_complexity() == "O(n^2)"


def test_recursion_without_memo_flagged_exponential():
    code = "def fib(n):\n    if n < 2:\n        return n\n    return fib(n-1) + fib(n-2)"
    sig = analyze("python", code)
    assert sig.has_recursion
    assert not sig.has_memoization
    assert "2^n" in sig.estimated_time_complexity()


def test_memoization_detected_by_decorator():
    code = "from functools import cache\n\n@cache\ndef fib(n):\n    return n if n < 2 else fib(n-1)+fib(n-2)"
    sig = analyze("python", code)
    assert sig.has_recursion
    assert sig.has_memoization


def test_data_structures_and_hashmap():
    code = "seen = {}\nfor i, x in enumerate([1,2,3]):\n    if x in seen:\n        seen.pop(x)\n    seen[x] = i"
    sig = analyze("python", code)
    assert "dict" in sig.data_structures
    assert sig.mutation_in_loop  # seen.pop inside loop


def test_syntax_error_is_reported_not_raised():
    sig = analyze("python", "for i in range(5)")  # missing colon
    assert not sig.parsed
    assert sig.error and "Syntax error" in sig.error
    assert sig.estimated_time_complexity() == "unknown"


def test_cpp_is_supported_via_treesitter():
    sig = analyze("cpp", "int main(){ for(int i=0;i<10;i++){} return 0; }")
    assert sig.parsed
    assert sig.max_loop_depth == 1


def test_genuinely_unsupported_language_is_honest():
    sig = analyze("ruby", "puts 'hi'")
    assert not sig.parsed
    assert "unsupported language" in (sig.error or "")


def test_looks_like_code_passes_prose_hints():
    prose = "For each value x, its partner must be target minus x."
    assert not looks_like_code(prose)


def test_looks_like_code_catches_snippets():
    snippet = "for i in range(n):\n    return i + 1"
    assert looks_like_code(snippet)
    assert looks_like_code("```python\nprint(1)\n```")


# --- memoisation detection ---------------------------------------------------

# Missing a memo table is not a cosmetic error. `has_memoization` gates the
# "unmemoized recursion recomputes identical subproblems" finding in the review
# and the skip-ahead in the hint ladder, so a false negative tells someone who
# did memoise that they did not, and re-teaches them a rung they are past.

MEMO_IDIOMS = {
    "parameter default": "def climb(n, memo={}):\n"
                         "    if n in memo: return memo[n]\n"
                         "    memo[n] = climb(n-1) + climb(n-2)\n"
                         "    return memo[n]\n",
    "subscript store": "def solve(n):\n"
                       "    dp = {}\n"
                       "    def go(k):\n"
                       "        if k in dp: return dp[k]\n"
                       "        dp[k] = go(k-1)\n"
                       "        return dp[k]\n"
                       "    return go(n)\n",
    "cache decorator": "from functools import cache\n@cache\ndef f(n): return f(n-1) + f(n-2)\n",
    "lru_cache decorator": "from functools import lru_cache\n@lru_cache(None)\ndef f(n): return f(n-1) + f(n-2)\n",
}


@pytest.mark.parametrize("idiom", sorted(MEMO_IDIOMS), ids=sorted(MEMO_IDIOMS))
def test_memoisation_is_detected(idiom):
    signals = analyze("python", MEMO_IDIOMS[idiom])
    assert signals.has_recursion
    assert signals.has_memoization, f"{idiom} memo table not detected"


def test_unmemoised_recursion_is_still_reported_as_such():
    """The fix must not turn the detector into one that always says yes."""
    signals = analyze("python", "def f(n):\n    if n < 2: return n\n    return f(n-1) + f(n-2)\n")
    assert signals.has_recursion
    assert not signals.has_memoization
    assert "2^n" in signals.estimated_time_complexity()


def test_memoised_recursion_is_not_estimated_as_constant_time():
    """It has no loop to count, so the loop-depth table read it as O(1) — and
    told everyone writing top-down DP that their solution was constant time."""
    signals = analyze("python", MEMO_IDIOMS["parameter default"])
    assert signals.estimated_time_complexity() == "O(n)"


def test_a_variable_named_memo_does_not_imply_recursion():
    signals = analyze("python", "def f(a):\n    memo = {}\n    for x in a: memo[x] = 1\n    return memo\n")
    assert not signals.has_recursion


# --- mutation: a counter is not a collection ---------------------------------

# `mutation_in_loop` used to be set by any augmented assignment, so `i += 1`
# reported "state is being mutated inside the loop". Nearly every loop ever
# written tripped it, which made the observation vacuous — and in the failure
# gallery it became "you are mutating what you are iterating over", which on
# two-pointer code is simply false.

MUTATION_CASES = {
    "counter_only": ("def f(s, t):\n"
                     "    c1 = 0\n    c2 = 0\n"
                     "    while c1 < len(s) and c2 < len(t):\n"
                     "        if s[c1] == t[c2]: c1 += 1\n"
                     "        c2 += 1\n"
                     "    return c1 == len(s)\n",
                     {"collection": False, "counter": True, "iterated": False}),
    "accumulator": ("def f(a):\n    total = 0\n    for x in a: total += x\n    return total\n",
                    {"collection": False, "counter": True, "iterated": False}),
    "builds_other_list": ("def f(a):\n    out = []\n    for x in a: out.append(x)\n    return out\n",
                          {"collection": True, "counter": False, "iterated": False}),
    "appends_to_iterated": ("def f(a):\n    for x in a: a.append(x)\n    return a\n",
                            {"collection": True, "counter": False, "iterated": True}),
    "writes_into_iterated": ("def f(a):\n    for i in range(len(a)): a[i] = 0\n    return a\n",
                             {"collection": True, "counter": False, "iterated": True}),
}


@pytest.mark.parametrize("name", sorted(MUTATION_CASES), ids=sorted(MUTATION_CASES))
def test_mutation_signals_distinguish_counters_from_collections(name):
    code, want = MUTATION_CASES[name]
    sig = analyze("python", code)
    assert sig.mutation_in_loop is want["collection"], f"{name}: collection mutation"
    assert sig.counter_update_in_loop is want["counter"], f"{name}: counter update"
    assert sig.mutates_iterated_collection is want["iterated"], f"{name}: iterated collection"


def test_two_pointer_code_is_not_accused_of_mutating_its_input():
    """The bug this split exists for."""
    from alfred.mentor import misconceptions

    sig = analyze("python", MUTATION_CASES["counter_only"][0])
    mistakes = " ".join(c["mistake"].lower() for c in misconceptions.derive(sig))
    assert "mutating what you are iterating over" not in mistakes


def test_code_that_really_does_mutate_its_input_is_still_caught():
    """The fix must not silence the genuine case."""
    from alfred.mentor import misconceptions

    sig = analyze("python", MUTATION_CASES["appends_to_iterated"][0])
    mistakes = " ".join(c["mistake"].lower() for c in misconceptions.derive(sig))
    assert "mutating what you are iterating over" in mistakes
