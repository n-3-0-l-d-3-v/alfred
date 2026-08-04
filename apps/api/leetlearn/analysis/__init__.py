"""Static analysis: turn source code into a small `CodeSignals` struct.

This is deliberately *not* the core of the product — it is a cheap, fast
grounding signal fed into the mentor so it can answer "is this O(n^2)?" and
diagnose misconceptions without an LLM round-trip. Python is implemented with
the stdlib `ast`; other languages arrive via tree-sitter in Phase 1.5 (the
`registry` seam is already in place).
"""

from .registry import analyze
from .signals import CodeSignals

__all__ = ["analyze", "CodeSignals"]
