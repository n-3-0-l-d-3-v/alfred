"""Review personas.

A review that only lists faults teaches very little. Each persona reframes the
same underlying findings for a different purpose:

  mentor       — warm, explains the *why* (default)
  roast        — funny, meme-forward, still technically correct
  interviewer  — answers with questions; makes you defend your choices
  pragmatist   — ship-it lens: is this good enough, and when would it not be
  professor    — formal: invariants, proof sketches, precise complexity

The findings are identical across personas — only voice and framing change, so
you can never get *wrong* feedback by picking a fun persona.
"""

from __future__ import annotations

from dataclasses import dataclass

MENTOR = "mentor"
ROAST = "roast"
INTERVIEWER = "interviewer"
PRAGMATIST = "pragmatist"
PROFESSOR = "professor"

ALL = [MENTOR, ROAST, INTERVIEWER, PRAGMATIST, PROFESSOR]


@dataclass
class Persona:
    key: str
    label: str
    blurb: str
    # headline templates: {est} actual complexity, {target} target complexity
    optimal: str
    suboptimal: str
    unparsed: str
    # how the "what breaks this" gallery is introduced
    failure_intro: str
    # how the follow-up challenges are introduced
    next_intro: str
    meme_tone: str  # which tone to request from the meme picker


_PERSONAS: dict[str, Persona] = {
    MENTOR: Persona(
        key=MENTOR,
        label="Mentor",
        blurb="Warm and explanatory. Tells you why, not just what.",
        optimal="This hits the target complexity ({est}). Here's why that matters and what to notice.",
        suboptimal="This works at {est}, and the target is {target}. That gap is the lesson — let's look at it.",
        unparsed="I couldn't parse this, so I'll stick to what the problem itself teaches.",
        failure_intro="Here's what would go wrong if you'd made one of the common mistakes:",
        next_intro="When you're ready to go deeper:",
        meme_tone="encourage",
    ),
    ROAST: Persona(
        key=ROAST,
        label="Roast",
        blurb="Funny, meme-forward, and never wrong about the technical bits.",
        optimal="{est}. Target was {target}. Nothing to make fun of. Disappointing.",
        suboptimal="{est} where {target} was on offer. Let's talk about it.",
        unparsed="Couldn't parse it. I'll assume that's the parser's fault and not yours.",
        failure_intro="Ways this could have gone badly (some of them nearly did):",
        next_intro="Prove it wasn't luck:",
        meme_tone="roast",
    ),
    INTERVIEWER: Persona(
        key=INTERVIEWER,
        label="Interviewer",
        blurb="Answers in questions. Makes you defend every choice.",
        optimal="You landed on {est}. Convince me it's optimal — what's the lower bound, and why?",
        suboptimal="You're at {est}; I'd expect {target}. Where is the wasted work, and what would you change first?",
        unparsed="I can't read this. Walk me through your approach out loud instead.",
        failure_intro="I'd probe these next — how does your code handle each?",
        next_intro="Follow-ups I'd ask in a real loop:",
        meme_tone="encourage",
    ),
    PRAGMATIST: Persona(
        key=PRAGMATIST,
        label="Pragmatist",
        blurb="Ship-it lens. Is this good enough, and when would it stop being?",
        optimal="{est} — optimal and readable. Ship it.",
        suboptimal="{est} vs a {target} target. Fine for small inputs; here's the scale where it stops being fine.",
        unparsed="Can't parse it, so I can't judge it. If it passes and reads clearly, that's usually enough.",
        failure_intro="Realistic failure modes, ranked by how likely they are to bite in production:",
        next_intro="Worth doing only if you'll hit these cases:",
        meme_tone="encourage",
    ),
    PROFESSOR: Persona(
        key=PROFESSOR,
        label="Professor",
        blurb="Formal. Invariants, correctness arguments, precise complexity.",
        optimal="Running time is {est}, matching the target {target}. Let us state the loop invariant that makes it correct.",
        suboptimal="Your procedure runs in {est}; an {target} algorithm exists. Consider what work is recomputed.",
        unparsed="The source could not be parsed; we will reason about the problem abstractly.",
        failure_intro="Cases in which the invariant fails:",
        next_intro="Exercises:",
        meme_tone="encourage",
    ),
}


def get(key: str | None) -> Persona:
    return _PERSONAS.get((key or MENTOR).lower(), _PERSONAS[MENTOR])


def catalog() -> list[dict]:
    return [{"key": p.key, "label": p.label, "blurb": p.blurb} for p in _PERSONAS.values()]
