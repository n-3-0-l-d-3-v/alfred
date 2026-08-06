"""The archetype definitions themselves.

Split from `archetypes.py` so the machinery stays readable as this file grows
toward full catalog coverage. Import order matters only in that every archetype
must be registered before a card referencing it is loaded, which
`mentor/__init__` guarantees by importing this module.

House rules for ladder text, enforced by tests:
  * No code, no pseudocode, no numbered transcribable steps. Prose about
    structure and intent only.
  * L4 may describe the shape of the approach. It may not describe the loop.
  * Nothing that reads as an assignment, a statement, or an arrow — those trip
    `looks_like_code`, and a card that trips it refuses to load.
"""

from __future__ import annotations

from .archetypes import Archetype, ApproachTemplate, LadderTemplate, register

# --- hashing / lookup --------------------------------------------------------

HASH_LOOKUP = register(Archetype(
    key="hash-lookup",
    name="Hash map / set lookup",
    summary="Trade memory for time by remembering what you have already seen.",
    pattern_hint="Something here is being searched for repeatedly",
    topics=("array", "hash-table"),
    target_time="O(n)",
    target_space="O(n)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="Walk through {collection} by hand for a moment. At each {unit}, what "
           "would you need to already know about the earlier ones to finish the job "
           "right there?",
        l2="The thing you need to know is {relationship}. Notice that it depends only "
           "on the current {unit} and on what came before — not on what comes after.",
        l3="The expensive part is going back over the earlier {collection} to answer "
           "that question again and again. Is there a structure that answers "
           "'have I seen this, and where?' in a single step instead of a scan?",
        l4="Make one pass. Before recording the current {unit}, ask whether what it "
           "needs is already recorded. If it is, you are done; if not, remember this "
           "one and carry on. Order matters — asking before remembering is what "
           "stops a {unit} from matching itself.",
    ),
    approaches=(
        ApproachTemplate(
            name="Brute force (compare every pair)",
            idea="Check {relationship} for every pair of {collection}.",
            time="O(n^2)", space="O(1)",
        ),
        ApproachTemplate(
            name="One-pass hash map",
            idea="Record each {unit} as you go; before recording, check whether what "
                 "it needs is already present.",
            time="O(n)", space="O(n)",
        ),
    ),
    pitfalls=(
        {"mistake": "Recording before checking",
         "why": "the current {unit} can then satisfy its own condition",
         "symptom": "an answer that pairs an element with itself"},
        {"mistake": "Keying the structure by value when values repeat",
         "why": "a later duplicate silently overwrites the earlier entry",
         "symptom": "wrong positions returned on inputs with duplicates"},
        {"mistake": "Returning the values when the problem asked for positions",
         "why": "the reasoning is right but the output shape is not",
         "symptom": "wrong answer despite finding the correct elements"},
    ),
    failure_cases=(
        {"mistake": "Recording the current {unit} before checking for what it needs",
         "trigger": "an input where one {unit} is exactly half of {goal}",
         "expected": "the pair of distinct positions",
         "actual": "the same position twice",
         "why": "You insert first, so the very next lookup finds the entry you just "
                "wrote. Check, then record."},
        {"mistake": "Assuming every value in {collection} is distinct",
         "trigger": "an input containing the same value twice",
         "expected": "both positions of the repeated value",
         "actual": "one position, or a missed match",
         "why": "A map keyed by value keeps only the most recent position. Whether "
                "that is a bug depends on whether you check before you overwrite."},
    ),
    edge_cases=(
        "An empty or single-element {collection}",
        "All values identical",
        "Negative values and zero",
        "The answer involving the very first and very last {unit}",
    ),
    rewrite_challenges=(
        "Solve it assuming {collection} is already sorted, using constant extra space.",
        "Return every distinct answer rather than just the first one.",
        "Argue whether the hash structure can be replaced by anything cheaper, and why.",
    ),
))

# --- two pointers ------------------------------------------------------------

TWO_POINTERS_CONVERGING = register(Archetype(
    key="two-pointers-converging",
    name="Converging two pointers",
    summary="Two indices walking toward each other over sorted or symmetric data.",
    pattern_hint="The ends of the data may be more informative than the middle",
    topics=("array", "two-pointers"),
    target_time="O(n)",
    target_space="O(1)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="Picture {collection} laid out in a line. If you only looked at the two "
           "ends, what could you already conclude about {goal}?",
        l2="Compare the two ends. One of those two {unit}s can be ruled out entirely "
           "by that single comparison — which one, and how do you know it can never "
           "be part of a better answer?",
        l3="Every time you rule one out, the problem shrinks by one. That means you "
           "never need to revisit it. What does that make the total amount of work, "
           "compared with checking every pair?",
        l4="Start with one marker at each end. Compare them, decide which end cannot "
           "improve the answer, and move that marker inward. Keep going until the "
           "markers meet. The ordering of {collection} is what makes the discarded "
           "side safe to discard.",
    ),
    approaches=(
        ApproachTemplate(
            name="Brute force (all pairs)",
            idea="Consider every pair of {unit}s and keep the best.",
            time="O(n^2)", space="O(1)",
        ),
        ApproachTemplate(
            name="Converging pointers",
            idea="Walk one marker from each end, discarding the side that cannot "
                 "improve {goal}.",
            time="O(n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Applying converging pointers to unsorted data",
         "why": "the discard argument depends on order",
         "symptom": "valid answers skipped entirely"},
        {"mistake": "Moving both markers at once",
         "why": "you can step over the answer without ever evaluating it",
         "symptom": "an off-by-one miss on small inputs"},
        {"mistake": "Getting the loop boundary wrong",
         "why": "whether the markers may land on the same {unit} is problem-specific",
         "symptom": "either a self-pairing or a missed final pair"},
    ),
    failure_cases=(
        {"mistake": "Using converging pointers without sorting first",
         "trigger": "an unsorted {collection} whose answer sits in the middle",
         "expected": "the correct pair",
         "actual": "no pair found",
         "why": "Convergence assumes that moving inward from a side can only make "
                "that side worse. Unsorted, that is simply untrue, so the markers "
                "move away from the answer."},
        {"mistake": "Letting both markers occupy the same position",
         "trigger": "a {collection} of length two",
         "expected": "the two distinct positions",
         "actual": "the same position counted twice",
         "why": "The stopping condition allowed the markers to meet and still be "
                "evaluated as a pair."},
    ),
    edge_cases=(
        "A {collection} of length zero, one, or two",
        "All {unit}s equal",
        "The answer at the extreme ends",
        "Duplicate values adjacent to the answer",
    ),
    rewrite_challenges=(
        "Solve it without sorting, and compare the complexity you end up with.",
        "Return all qualifying pairs rather than the best one, avoiding duplicates.",
        "Explain in one paragraph why discarding a side is provably safe.",
    ),
))

FAST_SLOW_POINTERS = register(Archetype(
    key="fast-slow-pointers",
    name="Fast and slow pointers",
    summary="Two traversal speeds over a sequence to find cycles, midpoints, or offsets.",
    pattern_hint="Position within the structure may matter more than the values",
    topics=("linked-list", "two-pointers"),
    target_time="O(n)",
    target_space="O(1)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="You are not allowed to know the length of {collection} in advance, and "
           "you want {goal}. What could two traversals moving at different speeds "
           "tell you that one traversal cannot?",
        l2="If one traverser covers ground twice as fast as the other, think about "
           "where the slower one is when the faster one finishes — or, if there is a "
           "loop, what must eventually happen to the gap between them.",
        l3="The naive route is to record every {unit} you visit so you can recognise "
           "a repeat. That works but costs memory proportional to the input. The two "
           "speeds give you the same information for free — why?",
        l4="Advance two markers through {collection} at different rates from the same "
           "start. The relationship between where they end up is the answer. No extra "
           "storage is needed, because the difference in their positions already "
           "encodes what you would otherwise have written down.",
    ),
    approaches=(
        ApproachTemplate(
            name="Record every visited node",
            idea="Store each visited {unit} and stop when one repeats.",
            time="O(n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Two traversal speeds",
            idea="Move two markers at different rates and read {goal} off their "
                 "relative positions.",
            time="O(n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Not checking the fast marker before advancing it",
         "why": "it can run off the end of {collection}",
         "symptom": "a crash on even-length or empty inputs"},
        {"mistake": "Assuming the meeting point is the answer",
         "why": "for cycle problems the meeting point is rarely the entry point",
         "symptom": "an answer that is consistently offset"},
        {"mistake": "Off-by-one on which marker to report",
         "why": "the two definitions of 'middle' differ on even lengths",
         "symptom": "wrong answer only on even-sized inputs"},
    ),
    failure_cases=(
        {"mistake": "Advancing the fast marker without checking it can move twice",
         "trigger": "a {collection} with an even number of {unit}s",
         "expected": "the correct result",
         "actual": "a null-reference crash",
         "why": "The fast marker steps past the end between checks. Both the marker "
                "and its next step have to exist before you move."},
        {"mistake": "Treating where the markers meet as where the loop begins",
         "trigger": "a {collection} whose loop starts partway in",
         "expected": "the first {unit} of the loop",
         "actual": "some other {unit} inside the loop",
         "why": "The meeting point depends on both the loop length and the distance "
                "to it. Recovering the entry needs a second, separate walk."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A single {unit}",
        "An even versus odd number of {unit}s",
        "A loop covering the entire {collection}",
    ),
    rewrite_challenges=(
        "Solve it again using extra storage, then compare the two for readability.",
        "Handle the even-length case with the opposite definition of the midpoint.",
        "Prove that the two markers must meet if a loop exists.",
    ),
))

# --- sliding window ----------------------------------------------------------

SLIDING_WINDOW_VARIABLE = register(Archetype(
    key="sliding-window-variable",
    name="Variable-size sliding window",
    summary="A window that grows and shrinks to maintain a condition over a contiguous run.",
    pattern_hint="The answer is a contiguous stretch, not a scattered selection",
    topics=("string", "sliding-window", "hash-table"),
    target_time="O(n)",
    target_space="O(k)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="The answer is a contiguous stretch of {collection}. How many such "
           "stretches are there in total, and can you afford to examine each one?",
        l2="Take a stretch that satisfies {condition}. Now extend it by one {unit} on "
           "the right. What is the smallest amount of work needed to know whether it "
           "still satisfies {condition} — do you really need to re-examine the whole "
           "stretch?",
        l3="When the stretch stops satisfying {condition}, the fix is never to start "
           "over from the next position. Everything you learned about the interior is "
           "still valid. What is the cheapest way to restore the condition?",
        l4="Maintain a window with two boundaries over {collection}. Extend the right "
           "boundary to take in new {unit}s. Whenever {condition} breaks, pull the "
           "left boundary in until it holds again. Each boundary only ever moves "
           "forward, which is why the total work stays linear.",
    ),
    approaches=(
        ApproachTemplate(
            name="Check every stretch",
            idea="Consider every start and end position and test {condition}.",
            time="O(n^2)", space="O(1)",
        ),
        ApproachTemplate(
            name="Sliding window",
            idea="Grow the window on the right, shrink on the left when {condition} "
                 "breaks, tracking the best as you go.",
            time="O(n)", space="O(k)",
        ),
    ),
    pitfalls=(
        {"mistake": "Resetting the window to empty when {condition} breaks",
         "why": "it discards interior work that was still valid",
         "symptom": "correct on small inputs, quadratic on large ones"},
        {"mistake": "Recording the best answer at the wrong moment",
         "why": "the window is only valid at particular points in the loop",
         "symptom": "an answer one larger or smaller than expected"},
        {"mistake": "Forgetting to update the running state when shrinking",
         "why": "the bookkeeping must mirror both boundaries",
         "symptom": "the window never recovers and the answer saturates"},
    ),
    failure_cases=(
        {"mistake": "Restarting the window from scratch after {condition} breaks",
         "trigger": "a long {collection} where the condition breaks near the end",
         "expected": "the correct longest stretch, computed in one pass",
         "actual": "the right answer, but after re-examining most of the input repeatedly",
         "why": "Correctness survives, complexity does not. This is the version that "
                "passes the samples and times out on the real constraints."},
        {"mistake": "Measuring the window before restoring {condition}",
         "trigger": "an input whose very first stretch already violates {condition}",
         "expected": "the best valid stretch",
         "actual": "a value counting an invalid window",
         "why": "The window is only a candidate answer at the moments it actually "
                "satisfies the condition."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A {collection} where no stretch satisfies {condition}",
        "The entire {collection} satisfying {condition}",
        "All {unit}s identical",
    ),
    rewrite_challenges=(
        "Return the stretch itself rather than only its size.",
        "Solve the fixed-size variant and note which parts of the logic disappear.",
        "Explain why each boundary moving forward only makes the total work linear.",
    ),
))

SLIDING_WINDOW_FIXED = register(Archetype(
    key="sliding-window-fixed",
    name="Fixed-size sliding window",
    summary="A window of constant width advanced one step at a time.",
    pattern_hint="A fixed span of the data is being examined repeatedly",
    topics=("array", "sliding-window"),
    target_time="O(n)",
    target_space="O(1)",
    brute_time="O(n*k)",
    ladder=LadderTemplate(
        l1="Every candidate answer covers exactly {width} consecutive {unit}s of "
           "{collection}. Write down two neighbouring candidates and compare them.",
        l2="Those two candidates overlap almost completely. Exactly one {unit} enters "
           "and one leaves. How much of the work you did for the first is genuinely "
           "reusable for the second?",
        l3="Recomputing from scratch for each position costs you the window width "
           "every time. If you only account for what entered and what left, what does "
           "each step cost instead?",
        l4="Compute the value for the first window directly. Then advance one position "
           "at a time, adjusting for the {unit} that just entered and the one that "
           "just left, keeping the best you have seen.",
    ),
    approaches=(
        ApproachTemplate(
            name="Recompute each window",
            idea="For every start position, examine all {width} {unit}s.",
            time="O(n*k)", space="O(1)",
        ),
        ApproachTemplate(
            name="Rolling window",
            idea="Adjust the running value for the {unit} entering and the one leaving.",
            time="O(n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Starting the slide before the first full window exists",
         "why": "the first {width} positions are still filling the window",
         "symptom": "an answer polluted by an undersized window"},
        {"mistake": "Removing the wrong {unit} when advancing",
         "why": "the departing index trails the arriving one by the window width",
         "symptom": "drift that grows the further in you go"},
        {"mistake": "Assuming {width} never exceeds the size of {collection}",
         "why": "no valid window exists in that case",
         "symptom": "a crash or a nonsense answer on short inputs"},
    ),
    failure_cases=(
        {"mistake": "Recording an answer before the window is full",
         "trigger": "a {collection} whose opening {unit}s are unusually favourable",
         "expected": "the best full-width window",
         "actual": "a better-looking value from a partial window",
         "why": "Only windows of exactly {width} are candidates. Positions before "
                "that are still filling it."},
        {"mistake": "Not handling a window wider than {collection}",
         "trigger": "a {collection} shorter than {width}",
         "expected": "an explicit empty or zero result",
         "actual": "an out-of-range access",
         "why": "The loop assumes at least one full window exists. Nothing guarantees "
                "that."},
    ),
    edge_cases=(
        "A window exactly as wide as {collection}",
        "A window wider than {collection}",
        "A window of width one",
        "All {unit}s identical",
    ),
    rewrite_challenges=(
        "Handle a window width supplied at runtime, including invalid values.",
        "Return every window that qualifies rather than only the best.",
        "Adapt it to a variable-width condition and note what has to change.",
    ),
))

# --- stacks ------------------------------------------------------------------

STACK_MATCHING = register(Archetype(
    key="stack-matching",
    name="Stack for nesting and matching",
    summary="Most-recent-first bookkeeping for nested or paired structure.",
    pattern_hint="The structure nests, so the most recent thing matters most",
    topics=("string", "stack"),
    target_time="O(n)",
    target_space="O(n)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="Read through {collection} left to right. When you reach a {unit} that "
           "closes something, which of all the still-open things does it belong to?",
        l2="It always belongs to the most recently opened one. That is a strong "
           "constraint — it means you never need to search the open items, only look "
           "at the newest.",
        l3="So you need a store where the only item you ever inspect or remove is the "
           "one added most recently. Which structure has exactly that shape, and "
           "nothing more?",
        l4="Walk {collection} once. Opening {unit}s get pushed aside for later. A "
           "closing {unit} must correspond to the most recently set-aside one — if it "
           "does not, the structure is already invalid. At the end, anything still "
           "set aside was never closed.",
    ),
    approaches=(
        ApproachTemplate(
            name="Repeatedly remove adjacent pairs",
            idea="Scan {collection} removing matched neighbours until nothing changes.",
            time="O(n^2)", space="O(n)",
        ),
        ApproachTemplate(
            name="Single pass with a stack",
            idea="Set aside each opening {unit}; match each closing one against the "
                 "most recent.",
            time="O(n)", space="O(n)",
        ),
    ),
    pitfalls=(
        {"mistake": "Forgetting to check for leftovers at the end",
         "why": "unclosed openings are just as invalid as mismatches",
         "symptom": "inputs that are all openings reported as valid"},
        {"mistake": "Removing from an empty store",
         "why": "a closing {unit} can arrive with nothing open",
         "symptom": "a crash rather than an invalid verdict"},
        {"mistake": "Checking only the count and not the kind",
         "why": "the right number of {unit}s can still be mismatched",
         "symptom": "mismatched but balanced inputs accepted"},
    ),
    failure_cases=(
        {"mistake": "Returning valid as soon as the scan finishes",
         "trigger": "an input consisting only of opening {unit}s",
         "expected": "invalid",
         "actual": "valid",
         "why": "Nothing ever mismatched because nothing ever closed. The leftovers "
                "are the failure, and they are only visible after the loop."},
        {"mistake": "Not guarding against closing with nothing open",
         "trigger": "an input beginning with a closing {unit}",
         "expected": "invalid",
         "actual": "a crash on the empty store",
         "why": "Emptiness has to be checked before removal, not after."},
    ),
    edge_cases=(
        "An empty {collection}",
        "Only opening {unit}s",
        "Only closing {unit}s",
        "Correctly balanced but deeply nested input",
    ),
    rewrite_challenges=(
        "Report the position of the first mismatch rather than a yes or no.",
        "Support a new pair of matching {unit}s without touching the loop.",
        "Explain why constant extra space is impossible for the general case.",
    ),
))

MONOTONIC_STACK = register(Archetype(
    key="monotonic-stack",
    name="Monotonic stack",
    summary="A stack kept in sorted order to answer next-greater and next-smaller queries.",
    pattern_hint="Each element seems to be waiting for a later one",
    topics=("array", "stack", "monotonic-stack"),
    target_time="O(n)",
    target_space="O(n)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="For each {unit} in {collection} you want {goal}, which depends on a later "
           "{unit}. Scanning forward from every position works — what makes it slow?",
        l2="Turn it around. When you arrive at a new {unit}, which of the earlier ones "
           "have just had their answer resolved by it? Often it is several at once.",
        l3="Those earlier {unit}s were waiting because nothing yet had exceeded them. "
           "That means the ones still waiting form a run in sorted order. What can you "
           "do with a store that always holds them in that order?",
        l4="Keep the unresolved {unit}s set aside in sorted order. Each new {unit} "
           "resolves every set-aside one it dominates, which you remove as you answer "
           "them, before setting the new one aside. Each {unit} is set aside once and "
           "removed once, which is what keeps the total linear.",
    ),
    approaches=(
        ApproachTemplate(
            name="Scan forward from each position",
            idea="For every {unit}, look rightward until {goal} is found.",
            time="O(n^2)", space="O(1)",
        ),
        ApproachTemplate(
            name="Monotonic stack",
            idea="Hold unresolved {unit}s in sorted order and resolve them in batches "
                 "as each new {unit} arrives.",
            time="O(n)", space="O(n)",
        ),
    ),
    pitfalls=(
        {"mistake": "Keeping the stack in the wrong order",
         "why": "the direction depends on whether you want a greater or smaller {goal}",
         "symptom": "answers that are correct only for the first element"},
        {"mistake": "Leaving unresolved items unanswered",
         "why": "some {unit}s never get resolved and need a default",
         "symptom": "missing or stale entries at the end"},
        {"mistake": "Storing values when positions are needed",
         "why": "distances and indices cannot be recovered from values alone",
         "symptom": "correct comparisons but unusable output"},
    ),
    failure_cases=(
        {"mistake": "Never assigning a default to items left on the stack",
         "trigger": "a {collection} in strictly decreasing order",
         "expected": "an explicit no-answer value for every position",
         "actual": "uninitialised or missing entries",
         "why": "Nothing ever resolves them, so the loop never touches them. What "
                "remains at the end has to be handled separately."},
        {"mistake": "Removing on the wrong comparison",
         "trigger": "a {collection} with adjacent equal values",
         "expected": "the problem's stated tie-breaking behaviour",
         "actual": "off-by-one or duplicated answers around the ties",
         "why": "Whether equal counts as resolving is a decision the problem makes "
                "for you, and it changes which comparison belongs in the loop."},
    ),
    edge_cases=(
        "A strictly increasing {collection}",
        "A strictly decreasing {collection}",
        "All values equal",
        "A single {unit}",
    ),
    rewrite_challenges=(
        "Solve the mirrored version (the other direction) by changing one comparison.",
        "Return distances rather than values.",
        "Argue why the total work is linear even though the inner removal is a loop.",
    ),
))
