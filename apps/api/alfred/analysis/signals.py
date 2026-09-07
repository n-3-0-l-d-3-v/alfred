"""The language-agnostic output of static analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class CodeSignals:
    language: str
    parsed: bool = True
    error: str | None = None

    loops: int = 0
    max_loop_depth: int = 0
    has_recursion: bool = False
    has_memoization: bool = False
    # A *collection* is grown, shrunk or written to inside a loop. Worth saying
    # something about.
    mutation_in_loop: bool = False
    # A scalar is advanced inside a loop — `i += 1`, `total += x`. This used to
    # be folded into `mutation_in_loop`, which meant essentially every loop ever
    # written reported "state is being mutated": vacuous as an observation, and
    # downstream it became the flatly false "you are mutating what you are
    # iterating over". Kept as its own signal because it is genuinely useful for
    # spotting a two-pointer walk, and useless as a warning.
    counter_update_in_loop: bool = False
    # The mutated collection is the one being iterated — the case that actually
    # causes skipped elements and index errors.
    mutates_iterated_collection: bool = False
    early_exit: bool = False

    data_structures: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)

    def estimated_time_complexity(self) -> str:
        """A rough, honest Big-O guess from loop nesting and recursion.

        This is a heuristic, not a proof. It is good enough to say "you're at
        O(n^2), the target is O(n)" — which is exactly the teaching signal we
        want — and it is clearly labelled as an estimate everywhere it surfaces.
        """
        if not self.parsed:
            return "unknown"
        if self.has_recursion and not self.has_memoization:
            return "O(2^n) or worse (unmemoized recursion)"
        if self.has_recursion and self.has_memoization and self.max_loop_depth == 0:
            # Memoised recursion has no loop to count, so the table below reads
            # it as O(1) — which told anyone who wrote top-down DP that their
            # solution was constant time. One pass over the distinct subproblems
            # is the honest rough answer; it understates multi-dimensional
            # states, which is the same kind of approximation as the rest of
            # this estimate and is labelled as such everywhere it surfaces.
            return "O(n)"
        table = {0: "O(1)", 1: "O(n)", 2: "O(n^2)", 3: "O(n^3)"}
        return table.get(self.max_loop_depth, f"O(n^{self.max_loop_depth})")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["estimated_time_complexity"] = self.estimated_time_complexity()
        return d
