"""Response contracts + the code-detection guard that enforces the AC gate.

`PreACHint` is the only thing the mentor may return before a passing
submission. Note what it does NOT have: no `code`, `solution`, or `pseudocode`
field. A learner literally cannot receive solution code through this object,
regardless of how the LLM is prompted or jailbroken. The `looks_like_code`
validator is defense-in-depth on top of that structural guarantee.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

# --- code detector -----------------------------------------------------------

_FENCE = "```"
# a keyword that opens a block/expr followed by a bracket or colon => code-ish
_STMT = re.compile(r"\b(def|class|return|import|from|for|while|if|elif|else|lambda|func|public|const|let|var)\b.*[:{(\[]")
# a line that *begins* with a control-flow statement keyword is code even with
# no bracket (e.g. "return i + 1"). These rarely open a prose sentence.
_STMT_LEAD = re.compile(r"^(return|break|continue|pass|yield|raise)\b")
_ASSIGN = re.compile(r"^[A-Za-z_][\w.\[\]]*\s*(=|\+=|-=|\*=|/=|:=)\s*\S")
_SEMI = re.compile(r";\s*$")
_ARROW = re.compile(r"=>|->")


def looks_like_code(text: str) -> bool:
    """True if `text` appears to contain a code snippet (not just a mention).

    Tuned so prose hints — even ones that say "hash map" or "target - x" —
    pass, while anything with an actual statement/assignment/code-fence fails.
    Two independent code-like lines are required, so a stray token can't trip it.
    """
    if _FENCE in text:
        return True
    code_lines = 0
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if _STMT.search(s) or _STMT_LEAD.match(s) or _ASSIGN.match(s) or _SEMI.search(s) or _ARROW.search(s):
            code_lines += 1
            if code_lines >= 2:
                return True
    return False


# --- pre-AC (Socratic only) --------------------------------------------------


class PreACHint(BaseModel):
    """A hint served before the problem is solved. Structurally code-free."""

    level: int
    kind: str = "ladder"  # ladder | socratic
    nudge: str            # a question or conceptual pointer — NEVER code
    source: str = "card"  # card (free) | llm (paid)
    hints_remaining_today: int = 0

    @field_validator("nudge")
    @classmethod
    def _no_code(cls, v: str) -> str:
        if looks_like_code(v):
            raise ValueError("pre-AC hint must not contain code (AC gate violation)")
        return v


# --- post-AC (firehose) ------------------------------------------------------


class ApproachOut(BaseModel):
    name: str
    idea: str
    time: str
    space: str
    code: str | None = None  # allowed — only ever reached after solved_at is set


class ReviewSection(BaseModel):
    """One lens on the code. Findings are identical across personas — only the
    surrounding voice changes — so a fun persona can never give wrong feedback."""

    lens: str  # correctness | complexity | robustness | idiom | alternatives
    title: str
    findings: list[str] = []


class FailureCase(BaseModel):
    """'What happens if you do it wrong' — a concrete, runnable-in-your-head
    demonstration rather than an abstract warning."""

    mistake: str
    trigger: str    # the input that exposes it
    expected: str
    actual: str
    why: str


class RichReview(BaseModel):
    persona: str
    persona_label: str
    headline: str
    verdict: str

    complexity_time: str
    complexity_space: str
    target_time: str

    sections: list[ReviewSection] = []
    failure_gallery: list[FailureCase] = []
    failure_intro: str = ""
    what_you_did_well: list[str] = []
    try_next: list[str] = []
    next_intro: str = ""

    meme: dict | None = None
    card_verified: bool = True
    source: str = "signals"  # signals (offline) | llm (enriched)


class PostACPayload(BaseModel):
    """Everything unlocked by a passing submission."""

    slug: str
    approaches: list[ApproachOut] = []
    pitfalls: list[dict] = []
    edge_cases: list[str] = []
    rewrite_challenges: list[str] = []
    complexity: dict = {}
