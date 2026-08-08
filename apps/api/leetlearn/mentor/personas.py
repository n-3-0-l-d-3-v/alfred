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

A persona controls four things, not just a headline:

  * which lens leads. An interviewer opens on what you cannot defend; a
    pragmatist opens on what will break in production; a professor opens on
    complexity. Order is most of what a voice *is* — it says what this reader
    thinks matters first.
  * what the sections are called.
  * how the failure gallery and follow-ups are introduced.
  * how it signs off.

Earlier versions changed only the headline sentence, which meant picking a
persona changed one line out of forty and the feature read as decorative.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MENTOR = "mentor"
DEADPAN = "deadpan"
ROAST = "roast"
INTERVIEWER = "interviewer"
PRAGMATIST = "pragmatist"
PROFESSOR = "professor"

ALL = [MENTOR, DEADPAN, ROAST, INTERVIEWER, PRAGMATIST, PROFESSOR]


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
    meme_tone: str  # which tone to request from the reaction picker

    # Which lens this voice leads with. Anything omitted keeps its natural
    # position after the listed ones.
    lens_order: tuple[str, ...] = ("complexity", "correctness", "robustness", "alternatives")
    # Per-lens section titles. A voice that calls it "What would break this"
    # and one that calls it "Adversarial cases" are not the same reader.
    section_titles: dict[str, str] = field(default_factory=dict)
    # A closing line, so the review ends in the persona's voice rather than
    # trailing off after the last bullet.
    closer: str = ""


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
        lens_order=("complexity", "correctness", "robustness", "alternatives"),
        section_titles={"robustness": "What would break this"},
        closer="You solved it. The rest of this is just what to carry into the next one.",
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
        lens_order=("complexity", "robustness", "alternatives", "correctness"),
        section_titles={
            "complexity": "The damage",
            "robustness": "Where it falls over",
            "alternatives": "What you could have done",
            "correctness": "Fine, credit where it's due",
        },
        closer="Anyway. It passed. Nobody can take that away from you, sadly.",
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
        # An interviewer opens on what you cannot yet defend, not on what went well.
        lens_order=("robustness", "complexity", "alternatives", "correctness"),
        section_titles={
            "robustness": "Where I'd push you",
            "complexity": "Justify the running time",
            "alternatives": "What else was on the table",
            "correctness": "Convince me it's right",
        },
        closer="In a real loop, the code is about a third of it. The rest is this conversation.",
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
        lens_order=("robustness", "correctness", "complexity", "alternatives"),
        section_titles={
            "robustness": "When this bites you",
            "correctness": "Does it actually work",
            "complexity": "Does the speed matter here",
            "alternatives": "Options, if you need them",
        },
        closer="Good enough is a real engineering answer. Knowing when it stops being good enough is the skill.",
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
        lens_order=("complexity", "correctness", "alternatives", "robustness"),
        section_titles={
            "complexity": "Asymptotic analysis",
            "correctness": "Correctness argument",
            "alternatives": "Alternative formulations",
            "robustness": "Cases in which it degrades",
        },
        closer="A solution you cannot explain is a solution you have not finished.",
    ),
    DEADPAN: Persona(
        key=DEADPAN,
        label="Deadpan",
        blurb="Dry, funny, never mean. The friend who's amused by the code, not by you.",
        # The distinction from Roast is the target. Roast is aimed at the
        # learner; this is aimed at the situation. Same jokes-per-paragraph,
        # no cost to the person reading it at 2am after four failed submissions.
        optimal="{est}, which is the target. Genuinely nothing to complain about. I had a whole thing prepared.",
        suboptimal="{est}. The target is {target}. Those are different numbers, and therein lies our topic.",
        unparsed="Couldn't parse it. Could be you, could be me, we may never know.",
        failure_intro="A short tour of adjacent realities where this went badly:",
        next_intro="If you're feeling brave:",
        lens_order=("complexity", "robustness", "correctness", "alternatives"),
        section_titles={
            "complexity": "How fast, and at what cost",
            "robustness": "Things that would ruin your afternoon",
            "correctness": "Evidence it works",
            "alternatives": "The roads not taken",
        },
        closer="That's the review. No notes, mostly.",
        meme_tone="encourage",
    ),
}


def get(key: str | None) -> Persona:
    return _PERSONAS.get((key or MENTOR).lower(), _PERSONAS[MENTOR])


def catalog() -> list[dict]:
    return [{"key": p.key, "label": p.label, "blurb": p.blurb} for p in _PERSONAS.values()]
