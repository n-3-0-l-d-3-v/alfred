"""Python static analysis via the stdlib `ast`.

Ported and extended from the original codeReview prototype: the loop-counting
and brute-force detection are kept; loop-depth, recursion, memoization, data
structures, mutation-in-loop, and early-exit are new.
"""

from __future__ import annotations

import ast

from .signals import CodeSignals

_LOOP_NODES = (ast.For, ast.While, ast.AsyncFor)
_MEMO_NAMES = {"memo", "dp", "cache"}
_MEMO_DECORATORS = {"cache", "lru_cache"}
_MUTATION_METHODS = {"append", "add", "pop", "update", "remove", "push", "extend", "insert"}


def _decorator_name(dec: ast.expr) -> str:
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        return dec.attr
    if isinstance(dec, ast.Call):
        return _decorator_name(dec.func)
    return ""


def _loop_depth(node: ast.AST, depth: int = 0) -> int:
    """Deepest nesting of loop constructs anywhere under `node`."""
    best = depth
    for child in ast.iter_child_nodes(node):
        step = 1 if isinstance(child, (_LOOP_NODES + (ast.comprehension,))) else 0
        best = max(best, _loop_depth(child, depth + step))
    return best


def analyze_python(code: str) -> CodeSignals:
    sig = CodeSignals(language="python")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        sig.parsed = False
        sig.error = f"Syntax error: {exc}"
        return sig

    variables: set[str] = set()
    data_structures: set[str] = set()
    patterns: set[str] = set()

    sig.max_loop_depth = _loop_depth(tree)

    func_defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for fn in func_defs:
        sig.functions.append(fn.name)
        # recursion: the function calls itself by name somewhere in its body
        for inner in ast.walk(fn):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == fn.name:
                sig.has_recursion = True
        # memoization via decorator
        for dec in fn.decorator_list:
            if _decorator_name(dec) in _MEMO_DECORATORS:
                sig.has_memoization = True

    for node in ast.walk(tree):
        # loop count (all loop-like constructs)
        if isinstance(node, (_LOOP_NODES + (ast.comprehension,))):
            sig.loops += 1

        # variables assigned
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            variables.add(node.id)
            if node.id.lower() in _MEMO_NAMES:
                sig.has_memoization = True
        elif isinstance(node, ast.arg):
            variables.add(node.arg)
            # `def climb(n, memo={})` — the commonest hand-rolled memo in Python
            # and, before this, invisible: the table is a parameter, so it is
            # never a Store Name anywhere in the function.
            if node.arg.lower() in _MEMO_NAMES:
                sig.has_memoization = True
        elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            # `memo[n] = ...`. The Store context belongs to the Subscript; the
            # table's name sits underneath it in Load context, so the Name branch
            # above never sees it as an assignment.
            base = node.value
            if isinstance(base, ast.Name) and base.id.lower() in _MEMO_NAMES:
                sig.has_memoization = True

        # data structures (literals + constructors + heapq usage)
        elif isinstance(node, ast.Dict):
            data_structures.add("dict")
        elif isinstance(node, ast.Set):
            data_structures.add("set")
        elif isinstance(node, ast.List):
            data_structures.add("list")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"set", "dict", "list", "tuple", "frozenset"}:
                data_structures.add(node.func.id)
            elif node.func.id in {"defaultdict", "Counter", "OrderedDict"}:
                data_structures.add("dict")
            elif node.func.id == "deque":
                data_structures.add("deque")
        elif isinstance(node, ast.Attribute) and node.attr in {"heappush", "heappop", "heapify"}:
            data_structures.add("heap")

    # per-loop inspection: mutation, early exit, brute-force search
    for loop in [n for n in ast.walk(tree) if isinstance(n, _LOOP_NODES)]:
        for inner in ast.walk(loop):
            if isinstance(inner, (ast.Break, ast.Return)):
                sig.early_exit = True
            elif isinstance(inner, ast.AugAssign):
                sig.mutation_in_loop = True
            elif isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                if inner.func.attr in _MUTATION_METHODS:
                    sig.mutation_in_loop = True
            elif isinstance(inner, ast.If):
                # brute-force linear search: an if inside a loop that breaks/returns
                for c in ast.walk(inner):
                    if isinstance(c, (ast.Break, ast.Return)):
                        patterns.add("brute force search")
                        break

    if sig.max_loop_depth >= 2:
        patterns.add("nested loops")

    sig.variables = sorted(variables)
    sig.data_structures = sorted(data_structures)
    sig.patterns = sorted(patterns)
    return sig
