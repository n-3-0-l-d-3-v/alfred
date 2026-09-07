"""Multi-language static analysis via tree-sitter.

Python keeps the stdlib-`ast` path (more precise: decorators, comprehensions);
everything else routes here. Node type names below were probed against the
actual installed grammars, not guessed.

tree-sitter is an *optional* dependency: if the import fails, `available()`
returns False and the registry degrades to an honest "not supported" signal
rather than crashing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .signals import CodeSignals

try:  # optional dependency
    from tree_sitter import Language, Parser

    import tree_sitter_cpp as _tscpp
    import tree_sitter_go as _tsgo
    import tree_sitter_java as _tsjava
    import tree_sitter_javascript as _tsjs
    import tree_sitter_python as _tspy

    _TS_OK = True
except Exception:  # pragma: no cover - depends on env
    _TS_OK = False


def available() -> bool:
    return _TS_OK


@dataclass
class LangSpec:
    module: object
    loops: set[str]
    funcs: set[str]
    calls: set[str]
    call_name_field: str = "function"
    returns: set[str] = field(default_factory=lambda: {"return_statement"})
    breaks: set[str] = field(default_factory=lambda: {"break_statement"})


_SPECS: dict[str, LangSpec] = {}
if _TS_OK:
    _SPECS = {
        "python": LangSpec(
            _tspy,
            loops={"for_statement", "while_statement", "for_in_clause"},
            funcs={"function_definition"},
            calls={"call"},
        ),
        "cpp": LangSpec(
            _tscpp,
            loops={"for_statement", "while_statement", "do_statement", "for_range_loop"},
            funcs={"function_definition"},
            calls={"call_expression"},
        ),
        "java": LangSpec(
            _tsjava,
            loops={"for_statement", "while_statement", "enhanced_for_statement", "do_statement"},
            funcs={"method_declaration"},
            calls={"method_invocation"},
            call_name_field="name",
        ),
        "javascript": LangSpec(
            _tsjs,
            loops={"for_statement", "while_statement", "for_in_statement", "do_statement"},
            funcs={"function_declaration", "function_expression", "arrow_function", "method_definition"},
            calls={"call_expression"},
        ),
        "go": LangSpec(
            _tsgo,
            loops={"for_statement"},
            funcs={"function_declaration", "method_declaration"},
            calls={"call_expression"},
        ),
    }

_ALIASES = {
    "c++": "cpp",
    "c": "cpp",
    "typescript": "javascript",
    "ts": "javascript",
    "js": "javascript",
    "golang": "go",
}

# identifier -> canonical data-structure name, across all languages
_DS_MAP = {
    # hash maps
    "dict": "dict", "defaultdict": "dict", "counter": "dict", "ordereddict": "dict",
    "hashmap": "dict", "unordered_map": "dict", "map": "dict", "treemap": "dict",
    # sets
    "set": "set", "frozenset": "set", "hashset": "set", "unordered_set": "set", "treeset": "set",
    # sequences
    "list": "list", "vector": "list", "arraylist": "list", "array": "list",
    # deques / queues
    "deque": "deque", "arraydeque": "deque", "linkedlist": "deque", "queue": "deque",
    # heaps
    "heapq": "heap", "heappush": "heap", "heappop": "heap",
    "priority_queue": "heap", "priorityqueue": "heap",
    # stacks
    "stack": "stack",
}

_MEMO_NAMES = {"memo", "dp", "cache", "memoized"}
_MUTATORS = {
    "append", "add", "push", "push_back", "insert", "emplace", "emplace_back",
    "put", "pop", "remove", "update", "extend", "offer", "addall",
}


def _text(node, src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf8", errors="replace")


def _func_name(node, src: bytes) -> str:
    """Function name across grammars. C++ hides it under a function_declarator."""
    n = node.child_by_field_name("name")
    if n is not None:
        return _text(n, src)
    decl = node.child_by_field_name("declarator")
    while decl is not None:
        ident = decl.child_by_field_name("declarator")
        if ident is None:
            return _text(decl, src).split("(")[0].strip()
        decl = ident
    return ""


def _call_name(node, spec: LangSpec, src: bytes) -> str:
    n = node.child_by_field_name(spec.call_name_field)
    if n is None:
        return ""
    txt = _text(n, src)
    # obj.method(...) -> method ; ns::fn(...) -> fn
    for sep in (".", "::", "->"):
        if sep in txt:
            txt = txt.split(sep)[-1]
    return txt.strip()


def analyze_with_treesitter(language: str, code: str) -> CodeSignals:
    lang = _ALIASES.get(language.lower(), language.lower())
    sig = CodeSignals(language=lang)

    if not _TS_OK or lang not in _SPECS:
        sig.parsed = False
        sig.error = f"no tree-sitter grammar loaded for '{language}'"
        return sig

    spec = _SPECS[lang]
    src = bytes(code, "utf8")
    parser = Parser(Language(spec.module.language()))
    tree = parser.parse(src)
    root = tree.root_node

    if root.has_error:
        # Still analyze — tree-sitter recovers from partial syntax errors, and a
        # learner mid-keystroke almost always has a broken parse.
        sig.error = "source has syntax errors; analysis is best-effort"

    data_structures: set[str] = set()
    patterns: set[str] = set()
    functions: list[str] = []
    variables: set[str] = set()

    # --- loop depth + loop count ---
    def walk_depth(node, depth: int) -> int:
        best = depth
        for child in node.children:
            step = 1 if child.type in spec.loops else 0
            if step:
                sig.loops += 1
            best = max(best, walk_depth(child, depth + step))
        return best

    sig.max_loop_depth = walk_depth(root, 0)

    # --- generic walk: identifiers, functions, calls ---
    func_nodes = []

    def walk(node):
        t = node.type
        if t in spec.funcs:
            func_nodes.append(node)
        # Only real identifiers/types name a data structure. Method names
        # (property_identifier / field_identifier) must NOT count, or `seen.set(x)`
        # would be misread as using a Set.
        if t in {"identifier", "type_identifier"}:
            raw = _text(node, src)
            key = raw.lower()
            if key in _DS_MAP:
                data_structures.add(_DS_MAP[key])
            if key in _MEMO_NAMES:
                sig.has_memoization = True
            variables.add(raw)
        elif t in {"field_identifier", "property_identifier"}:
            variables.add(_text(node, src))
        for c in node.children:
            walk(c)

    walk(root)

    for fn in func_nodes:
        name = _func_name(fn, src)
        if name:
            functions.append(name)
        # recursion: does this function call itself?
        def find_calls(node):
            if node.type in spec.calls:
                if name and _call_name(node, spec, src) == name:
                    sig.has_recursion = True
            for c in node.children:
                find_calls(c)

        find_calls(fn)

    # python decorator-based memoization (also reachable via tree-sitter path)
    if lang == "python" and ("lru_cache" in code or "@cache" in code):
        sig.has_memoization = True

    # --- inside-loop behaviour ---
    def scan_loop(node):
        if node.type in spec.returns or node.type in spec.breaks:
            sig.early_exit = True
        # `i++` and `total += x` advance a counter; they do not mutate a
        # collection. Conflating the two made every loop in every language
        # report "state is being mutated", which says nothing.
        if node.type in {"augmented_assignment", "update_expression",
                         "assignment_expression", "inc_dec_expression"}:
            sig.counter_update_in_loop = True
        if node.type in spec.calls:
            if _call_name(node, spec, src).lower() in _MUTATORS:
                sig.mutation_in_loop = True
        for c in node.children:
            scan_loop(c)

    def find_loops(node):
        if node.type in spec.loops:
            scan_loop(node)
        for c in node.children:
            find_loops(c)

    find_loops(root)

    if sig.max_loop_depth >= 2:
        patterns.add("nested loops")
    if sig.early_exit and sig.max_loop_depth >= 1:
        patterns.add("brute force search")

    sig.functions = functions
    sig.variables = sorted(variables)[:50]  # cap noise
    sig.data_structures = sorted(data_structures)
    sig.patterns = sorted(patterns)
    return sig
