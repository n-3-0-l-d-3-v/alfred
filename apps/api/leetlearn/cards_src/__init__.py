"""Problem card specializations, grouped by archetype.

Each module here holds `Spec` objects — the small per-problem half of a card
(the nouns its archetype's templates need, a plain-language restatement, and the
solution code for each approach). The archetype supplies everything else.

Grouping by archetype rather than by difficulty or list membership is
deliberate: the specializations for one pattern share vocabulary, so writing
them together keeps the nouns consistent, and a fix to how a pattern is taught
lands in one place and propagates to every problem using it.

`ALL` is what the loader reads. Adding a problem means appending one Spec.
"""

from __future__ import annotations

from ..mentor.card_builder import Spec
from . import arrays_hashing, graphs, sliding_window, stack_and_pointers, trees

ALL: list[Spec] = [
    *arrays_hashing.SPECS,
    *sliding_window.SPECS,
    *stack_and_pointers.SPECS,
    *trees.SPECS,
    *graphs.SPECS,
]
