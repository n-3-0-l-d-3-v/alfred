"""Pull the worked examples out of a problem statement.

Every LeetCode statement ships two or three of them — "Input: s = "abc", t =
"ahbgdc"  Output: true" — and until now the product ignored them completely. That
is most of why the teaching reads as generic: a failure case that says "an input
at the top of the stated constraints" is a sentence about problems in general,
while one that says "try s = "axc", t = "ahbgdc"" is about the problem on screen.
They cost nothing — the statement is already fetched for archetype inference.

They are also the only ground truth we have about the problem's actual semantics.
The archetype knows the pattern and the analyser knows the code's shape; neither
knows what this problem returns for any specific input. The examples do.

Parsing is deliberately forgiving and always optional. A statement that does not
match these shapes yields nothing and every caller falls back to what it said
before — a missed example costs a little specificity, while a mis-parsed one
would put a wrong claim about expected output in front of a learner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "Input: nums = [2,7,11,15], target = 9 Output: [0,1] Explanation: ..."
# The statement arrives as flattened text (see the extension's stripHtml), so
# the labels are the only structure left to anchor on.
_EXAMPLE = re.compile(
    r"Input:\s*(?P<input>.+?)\s*Output:\s*(?P<output>.+?)"
    r"(?=\s*(?:Explanation:|Example\s*\d|Constraints:|Input:|$))",
    re.I | re.S,
)
_EXPLANATION = re.compile(r"Explanation:\s*(?P<text>.+?)(?=\s*(?:Example\s*\d|Constraints:|Input:|$))", re.I | re.S)

# Splitting an argument list on commas is wrong the moment a list literal shows
# up — "nums = [2,7,11,15], target = 9" is two arguments, not five. Only commas
# at bracket depth zero separate arguments.
_ASSIGN = re.compile(r"^\s*(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<value>.+)$", re.S)

MAX_VALUE_CHARS = 120


@dataclass(frozen=True)
class Example:
    """One worked example, as the statement gave it."""

    args: dict[str, str]
    output: str
    explanation: str | None = None

    def render_input(self) -> str:
        """The input as a learner would type it into the test box."""
        return ", ".join(f"{k} = {v}" for k, v in self.args.items())

    @property
    def is_usable(self) -> bool:
        """Short enough to quote inside a sentence.

        A 40-element array pasted into a failure case makes the case unreadable,
        which defeats the point of quoting a concrete input at all.
        """
        return (
            bool(self.args)
            and bool(self.output)
            and len(self.render_input()) <= MAX_VALUE_CHARS
            and len(self.output) <= 40
        )


def _split_args(text: str) -> list[str]:
    """Split on top-level commas only, so list and object literals survive."""
    parts, depth, current = [], 0, []
    for char in text:
        if char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


# A bare value with no parameter name — "Input: [1,2,3]" — is a real shape, but
# accepting anything unnamed also accepts prose: "The Input: is described above.
# Output: should be returned." parsed as a perfectly good example. A literal
# starts with a bracket, a quote, or a number, and never ends a sentence.
_LITERAL = re.compile(r'^[\[\{"\'\d-]')


def _looks_like_a_value(text: str) -> bool:
    return bool(_LITERAL.match(text)) and not text.rstrip().endswith(".")


def _parse_args(text: str) -> dict[str, str]:
    args: dict[str, str] = {}
    for part in _split_args(text):
        match = _ASSIGN.match(part)
        if match:
            args[match.group("name")] = " ".join(match.group("value").split())
        elif len(args) == 0 and _looks_like_a_value(part):
            args["input"] = " ".join(part.split())
    return args


def parse(statement: str | None, limit: int = 3) -> list[Example]:
    """Every worked example in `statement`, in the order it presents them."""
    if not statement:
        return []

    out: list[Example] = []
    explanations = [m.group("text").strip() for m in _EXPLANATION.finditer(statement)]

    for i, match in enumerate(_EXAMPLE.finditer(statement)):
        args = _parse_args(match.group("input"))
        output = " ".join(match.group("output").split())
        if not args or not output:
            continue
        example = Example(
            args=args,
            output=output,
            explanation=explanations[i] if i < len(explanations) else None,
        )
        if example.is_usable:
            out.append(example)
        if len(out) >= limit:
            break
    return out


def concrete_trigger(examples: list[Example], fallback: str) -> str:
    """A real input to quote in a failure case, or the generic phrasing.

    Always falls back rather than guessing. "An input where one value repeats"
    is vague but true; a fabricated input that does not match the problem's
    actual signature is specific and wrong, which is worse.
    """
    for example in examples:
        return example.render_input()
    return fallback
