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

# --- binary search -----------------------------------------------------------

BINARY_SEARCH_SORTED = register(Archetype(
    key="binary-search-sorted",
    name="Binary search over sorted data",
    summary="Halve the search space using an ordering guarantee.",
    pattern_hint="The input is ordered, and that ordering is probably the point",
    topics=("array", "binary-search"),
    target_time="O(log n)",
    target_space="O(1)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="{collection} is ordered. Look at the {unit} in the exact middle and "
           "compare it with {goal}. What have you learned about the two halves?",
        l2="One of those halves cannot possibly contain the answer, and the ordering "
           "is what tells you which. Discarding it costs nothing.",
        l3="Each comparison throws away half of what remains. Starting from a million "
           "{unit}s, roughly how many comparisons before only one is left?",
        l4="Track the range still under consideration. Repeatedly inspect its middle, "
           "decide which side can be eliminated, and narrow the range accordingly. "
           "The two decisions that matter are whether the middle itself stays in the "
           "range, and what to report when the range empties.",
    ),
    approaches=(
        ApproachTemplate(
            name="Linear scan",
            idea="Examine every {unit} until {goal} is located.",
            time="O(n)", space="O(1)",
        ),
        ApproachTemplate(
            name="Binary search",
            idea="Halve the remaining range at each comparison against the middle {unit}.",
            time="O(log n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "An inconsistent range convention",
         "why": "mixing inclusive and exclusive ends breaks the loop's invariant",
         "symptom": "an infinite loop or a missed final {unit}"},
        {"mistake": "Excluding the middle when it might be the answer",
         "why": "the eliminated half must provably not contain it",
         "symptom": "the answer missed when it sits exactly at a midpoint"},
        {"mistake": "Not defining what happens when nothing matches",
         "why": "many variants want an insertion position rather than a failure",
         "symptom": "correct on hits, wrong on misses"},
    ),
    failure_cases=(
        {"mistake": "Narrowing the range without ever excluding the middle",
         "trigger": "a two-{unit} {collection} where the answer is the second",
         "expected": "the correct position",
         "actual": "the loop never terminates",
         "why": "The range stops shrinking once it holds two items, so the midpoint "
                "stays put and the same comparison repeats forever."},
        {"mistake": "Assuming the answer is always present",
         "trigger": "a {goal} that does not appear in {collection}",
         "expected": "the documented not-found result",
         "actual": "whatever happened to be at the final position",
         "why": "The loop ends when the range empties, which is a different outcome "
                "from finding something. It has to be reported differently."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A single {unit}",
        "{goal} smaller than everything, or larger than everything",
        "Duplicate values around {goal}",
    ),
    rewrite_challenges=(
        "Return the insertion position when {goal} is absent.",
        "Find the first and last occurrence when duplicates exist.",
        "State the loop invariant your range convention maintains, precisely.",
    ),
))

BINARY_SEARCH_ON_ANSWER = register(Archetype(
    key="binary-search-on-answer",
    name="Binary search on the answer",
    summary="Search the space of possible answers rather than the input.",
    pattern_hint="Checking a candidate answer looks easier than constructing one",
    topics=("array", "binary-search", "greedy"),
    target_time="O(n log m)",
    target_space="O(1)",
    brute_time="O(n*m)",
    ladder=LadderTemplate(
        l1="Constructing {goal} directly is hard. Try an easier question instead: "
           "given a specific candidate value, could you check whether it works?",
        l2="Suppose a candidate works. What can you say about every larger candidate — "
           "and if it fails, what about every smaller one? That property is the whole "
           "problem.",
        l3="That yes-or-no answer is monotonic across the range of candidates: false "
           "everywhere below some boundary, true everywhere above it. You are looking "
           "for that boundary. What does that let you stop doing?",
        l4="Establish the range of conceivable answers. Repeatedly test the middle "
           "candidate with your checking routine, keep the half that still contains "
           "the boundary, and narrow until one candidate remains. The checker is "
           "where the real problem lives; the search around it is mechanical.",
    ),
    approaches=(
        ApproachTemplate(
            name="Try every candidate",
            idea="Test each possible answer in order until one works.",
            time="O(n*m)", space="O(1)",
        ),
        ApproachTemplate(
            name="Binary search the answer space",
            idea="Exploit that feasibility is monotonic in the candidate to halve the "
                 "range each time.",
            time="O(n log m)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Searching a range that excludes the true answer",
         "why": "the bounds must be provably wide enough",
         "symptom": "answers pinned to one end of the range"},
        {"mistake": "A checker that is not actually monotonic",
         "why": "binary search is meaningless without that property",
         "symptom": "answers that vary with unrelated details of the input"},
        {"mistake": "Returning the last tested candidate",
         "why": "the boundary is not necessarily the final midpoint",
         "symptom": "an answer consistently off by one"},
    ),
    failure_cases=(
        {"mistake": "Starting the range at one instead of the smallest feasible value",
         "trigger": "an input whose answer must be at least as large as its biggest {unit}",
         "expected": "the true minimum",
         "actual": "an infeasible value at the bottom of the range",
         "why": "The search can only return something inside its range. If the answer "
                "was never in it, no amount of correct halving finds it."},
        {"mistake": "Checking feasibility with a subtly different condition",
         "trigger": "an input sitting exactly on the boundary",
         "expected": "the boundary value",
         "actual": "one either side of it",
         "why": "The checker defines the boundary. A strict comparison where the "
                "problem allows equality moves it by exactly one."},
    ),
    edge_cases=(
        "The answer equal to the lower bound",
        "The answer equal to the upper bound",
        "A single {unit}",
        "All {unit}s identical",
    ),
    rewrite_challenges=(
        "State and justify the bounds of your search range.",
        "Prove the checker is monotonic, or find the input where it is not.",
        "Solve the maximising variant and note which comparisons flip.",
    ),
))

# --- heaps -------------------------------------------------------------------

HEAP_TOP_K = register(Archetype(
    key="heap-top-k",
    name="Heap for top-k and streaming order",
    summary="Maintain the k best seen so far without sorting everything.",
    pattern_hint="Only a few of the values actually matter",
    topics=("array", "heap", "sorting"),
    target_time="O(n log k)",
    target_space="O(k)",
    brute_time="O(n log n)",
    ladder=LadderTemplate(
        l1="You want the best {width} {unit}s of {collection}, not all of them in "
           "order. How much of a full sort is genuinely useful to you?",
        l2="Hold onto {width} candidates as you scan. When a new {unit} arrives, the "
           "only one it could displace is the weakest of the ones you are holding. "
           "Which operations do you actually need on that group?",
        l3="You need the weakest of the group, and you need to replace it — nothing "
           "else. You never need the group fully ordered. What structure gives you "
           "exactly those two operations cheaply?",
        l4="Keep a group of at most {width} candidates that can surrender its weakest "
           "member on demand. Scan {collection} once, admitting each new {unit} only "
           "when it beats that weakest member, and evicting the weakest to stay at "
           "{width}. What remains is the answer.",
    ),
    approaches=(
        ApproachTemplate(
            name="Sort everything",
            idea="Order all of {collection} and take the first {width}.",
            time="O(n log n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Bounded heap",
            idea="Keep only {width} candidates, evicting the weakest as better {unit}s "
                 "arrive.",
            time="O(n log k)", space="O(k)",
        ),
    ),
    pitfalls=(
        {"mistake": "Using the wrong heap direction",
         "why": "keeping the largest {width} needs the smallest at the top",
         "symptom": "exactly the wrong {width} {unit}s returned"},
        {"mistake": "Letting the heap grow beyond {width}",
         "why": "the space and time advantage disappears",
         "symptom": "correct answers with no complexity gain"},
        {"mistake": "Comparing on the wrong field for tuples",
         "why": "ordering follows the first field by default",
         "symptom": "plausible but incorrectly ranked output"},
    ),
    failure_cases=(
        {"mistake": "Keeping a heap ordered the same way as the answer",
         "trigger": "any {collection} longer than {width}",
         "expected": "the best {width} {unit}s",
         "actual": "the worst {width}",
         "why": "To keep the largest values you must be able to discard the smallest "
                "of what you hold, so the top of the heap has to be the smallest."},
        {"mistake": "Not handling a {width} larger than {collection}",
         "trigger": "a {collection} with fewer than {width} {unit}s",
         "expected": "everything, in the required order",
         "actual": "an error or a short result",
         "why": "The eviction step assumes the heap is full, which it never becomes."},
    ),
    edge_cases=(
        "{width} equal to one",
        "{width} equal to the size of {collection}",
        "{width} larger than {collection}",
        "Ties on the boundary of the top {width}",
    ),
    rewrite_challenges=(
        "Solve it with sorting and compare the complexities honestly.",
        "Support a stream where {collection} does not fit in memory.",
        "Return the k-th value only, and note what work becomes unnecessary.",
    ),
))

# --- intervals ---------------------------------------------------------------

MERGE_INTERVALS = register(Archetype(
    key="merge-intervals",
    name="Interval sorting and sweeping",
    summary="Order intervals by an endpoint, then make one pass deciding overlaps.",
    pattern_hint="The order the ranges arrive in is probably not the useful order",
    topics=("array", "intervals", "sorting"),
    target_time="O(n log n)",
    target_space="O(n)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="The ranges arrive in arbitrary order. Comparing every range with every "
           "other works. Before optimising, ask what order would make the comparisons "
           "unnecessary.",
        l2="Sort them by where they start. Now, walking left to right, how many of the "
           "ranges you have already passed could still overlap the one in front of you?",
        l3="Only the reach of what you have accumulated so far matters — everything "
           "further left is settled and can never overlap anything ahead. So the state "
           "you carry is tiny. What exactly is it?",
        l4="Order the ranges by start. Carry one accumulated range forward. Each new "
           "range either touches it, in which case the accumulated reach extends, or "
           "it does not, in which case the accumulated one is final and the new one "
           "takes over. The definition of touching is where the problem hides.",
    ),
    approaches=(
        ApproachTemplate(
            name="Compare all pairs",
            idea="Test every pair of ranges for overlap and merge repeatedly.",
            time="O(n^2)", space="O(n)",
        ),
        ApproachTemplate(
            name="Sort and sweep",
            idea="Order by start, then make one pass extending or closing the "
                 "accumulated range.",
            time="O(n log n)", space="O(n)",
        ),
    ),
    pitfalls=(
        {"mistake": "Sorting by the wrong endpoint",
         "why": "start order is what makes a single pass sufficient",
         "symptom": "merges missed when a long range precedes a short one"},
        {"mistake": "Getting touching-versus-overlapping wrong",
         "why": "whether shared endpoints merge is problem-specific",
         "symptom": "off-by-one merges at the boundaries"},
        {"mistake": "Forgetting the final accumulated range",
         "why": "the loop closes ranges only when a new one fails to touch",
         "symptom": "the last range always missing from the output"},
    ),
    failure_cases=(
        {"mistake": "Never emitting the range still accumulating when the loop ends",
         "trigger": "any input whose last two ranges overlap",
         "expected": "all merged ranges including the final one",
         "actual": "the output missing its last entry",
         "why": "Ranges are emitted when something fails to touch them. The final one "
                "has nothing after it, so it must be emitted explicitly."},
        {"mistake": "Treating ranges that merely touch as separate",
         "trigger": "two ranges where one ends exactly where the next begins",
         "expected": "a single merged range, if the problem counts touching as overlap",
         "actual": "two ranges",
         "why": "This is entirely a matter of strict versus non-strict comparison, and "
                "the problem statement decides it, not intuition."},
    ),
    edge_cases=(
        "A single range",
        "Ranges that are entirely contained in others",
        "Ranges sharing exactly one endpoint",
        "Already-sorted and reverse-sorted input",
    ),
    rewrite_challenges=(
        "Return the gaps between ranges rather than the merged ranges.",
        "Insert one new range into an already-merged list without re-sorting.",
        "Find the maximum number of ranges overlapping at any single point.",
    ),
))

# --- linked lists ------------------------------------------------------------

LINKED_LIST_REWIRING = register(Archetype(
    key="linked-list-rewiring",
    name="Pointer rewiring on a linked list",
    summary="Re-aim the links themselves rather than moving any data.",
    pattern_hint="The links matter more than the values they carry",
    topics=("linked-list",),
    target_time="O(n)",
    target_space="O(1)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="You cannot index into {collection} — you can only follow links forward. "
           "Given that, what is the one thing you lose the instant you re-aim a link?",
        l2="You lose the rest of the list. So before changing any link, you need to "
           "have already secured what it currently points at. How many things must you "
           "hold at once to change one link safely?",
        l3="Three positions is enough: what came before, where you are, and what comes "
           "next. Copying the whole structure into an array also works — what does that "
           "cost you that the three-marker version does not?",
        l4="Advance through {collection} once, carrying markers for the previous and "
           "next positions. At each step, secure the next position first, then re-aim "
           "the current link backward, then shift all the markers forward. The order of "
           "those three actions is the entire problem.",
    ),
    approaches=(
        ApproachTemplate(
            name="Copy into an array",
            idea="Read every {unit} into a list, rearrange, and rebuild.",
            time="O(n)", space="O(n)",
        ),
        ApproachTemplate(
            name="In-place rewiring",
            idea="Carry previous and next markers and re-aim each link during one pass.",
            time="O(n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Re-aiming a link before securing what follows it",
         "why": "the remainder of {collection} becomes unreachable",
         "symptom": "a truncated result or a lost list"},
        {"mistake": "Returning the original head",
         "why": "after rewiring it is the tail",
         "symptom": "a result containing a single {unit}"},
        {"mistake": "Not handling an empty or single-{unit} list",
         "why": "the marker dance assumes at least two positions",
         "symptom": "a null-reference crash on the smallest inputs"},
    ),
    failure_cases=(
        {"mistake": "Re-aiming the current link before saving the next position",
         "trigger": "any {collection} with more than one {unit}",
         "expected": "the fully rewired list",
         "actual": "a list of one or two {unit}s",
         "why": "The link you overwrote was the only route to the remainder. Once it "
                "is gone the rest is unreachable, so the traversal stops immediately."},
        {"mistake": "Returning the node you started from",
         "trigger": "any non-empty {collection}",
         "expected": "the new head",
         "actual": "a single {unit}",
         "why": "The node you began at ends up last. The new head is whatever the "
                "traversal was holding when it ran out of list."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A single {unit}",
        "Exactly two {unit}s",
        "Duplicate values throughout",
    ),
    rewrite_challenges=(
        "Solve it recursively and compare the space cost honestly.",
        "Reverse only a sub-range, leaving the rest intact.",
        "Explain why a dummy leading node simplifies the boundary handling.",
    ),
))

# --- trees -------------------------------------------------------------------

TREE_DFS = register(Archetype(
    key="tree-dfs",
    name="Depth-first recursion on a tree",
    summary="Solve a tree problem by combining the answers from its subtrees.",
    pattern_hint="The whole may be answerable from its parts",
    topics=("tree", "depth-first-search", "recursion"),
    target_time="O(n)",
    target_space="O(h)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="Suppose someone handed you the correct answer for the left subtree and the "
           "correct answer for the right subtree, for free. Could you produce {goal} "
           "for the whole tree from just those two values and the current {unit}?",
        l2="That combining step is the entire problem. Write it out in words for one "
           "node before writing anything else — what exactly do you do with the two "
           "answers you were handed?",
        l3="Now the base case. What is {goal} for a tree with no {unit}s at all? Get "
           "this wrong and every answer above it inherits the error.",
        l4="Recurse into both subtrees, then combine their results with the current "
           "{unit} using the rule you described. Each {unit} is visited once. The one "
           "subtlety is whether the value you return upward is the same thing as the "
           "answer you are accumulating — for many tree problems it is not.",
    ),
    approaches=(
        ApproachTemplate(
            name="Recursive depth-first",
            idea="Combine subtree results at each {unit}.",
            time="O(n)", space="O(h)",
        ),
        ApproachTemplate(
            name="Iterative with an explicit stack",
            idea="Simulate the recursion to avoid depth limits.",
            time="O(n)", space="O(h)",
        ),
    ),
    pitfalls=(
        {"mistake": "Missing or wrong base case",
         "why": "the empty tree is the foundation every other answer rests on",
         "symptom": "answers off by a constant, or infinite recursion"},
        {"mistake": "Confusing the returned value with the accumulated answer",
         "why": "many tree problems track a global best separately from what each "
                "call reports upward",
         "symptom": "correct on small trees, wrong when the best path avoids the root"},
        {"mistake": "Ignoring recursion depth on a degenerate tree",
         "why": "a tree shaped like a list is as deep as it is large",
         "symptom": "a stack overflow only on large skewed inputs"},
    ),
    failure_cases=(
        {"mistake": "Returning the accumulated best instead of the value the parent needs",
         "trigger": "a tree whose best answer lies entirely within one subtree",
         "expected": "the true best across the whole tree",
         "actual": "a value that only makes sense as a path through the root",
         "why": "The parent needs a value it can extend. The answer you are tracking "
                "may not be extendable. Those are two different quantities and they "
                "need two different variables."},
        {"mistake": "Treating a missing child as an error rather than a base case",
         "trigger": "any tree with a node having exactly one child",
         "expected": "the correct combined answer",
         "actual": "a null-reference crash",
         "why": "Absence is a legitimate subtree, and it has a well-defined answer. "
                "Handling it as a value rather than a special case removes most of "
                "the branching."},
    ),
    edge_cases=(
        "An empty tree",
        "A single {unit}",
        "A tree degenerate into a straight line",
        "A perfectly balanced tree",
    ),
    rewrite_challenges=(
        "Rewrite it iteratively with an explicit stack.",
        "Return the path achieving {goal}, not just its value.",
        "State what each recursive call promises its caller, in one sentence.",
    ),
))

TREE_BFS = register(Archetype(
    key="tree-bfs",
    name="Breadth-first traversal by level",
    summary="Process a tree one full level at a time.",
    pattern_hint="Distance from the root looks like it matters",
    topics=("tree", "breadth-first-search", "queue"),
    target_time="O(n)",
    target_space="O(w)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="{goal} depends on how far each {unit} sits from the root. Depth-first "
           "recursion wanders deep before it goes wide — does that visit order help "
           "you here?",
        l2="You want to finish an entire level before starting the next. That means "
           "processing {unit}s in the order they were discovered. Which discipline "
           "does that describe: newest-first, or oldest-first?",
        l3="Oldest-first gives you level order automatically. But to answer per-level "
           "questions you need to know where one level ends. What do you already know "
           "at the top of each round that tells you that?",
        l4="Keep a pending group, seeded with the root. Each round, note how many "
           "{unit}s are pending — that count is exactly the current level — and process "
           "precisely that many, adding their children for the next round. Capturing "
           "the count before processing is what keeps the levels separate.",
    ),
    approaches=(
        ApproachTemplate(
            name="Depth-first with a depth parameter",
            idea="Recurse, bucketing each {unit} by its depth.",
            time="O(n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Level-by-level breadth-first",
            idea="Process a whole level per round using the pending count as the "
                 "level boundary.",
            time="O(n)", space="O(w)",
        ),
    ),
    pitfalls=(
        {"mistake": "Reading the pending count after adding children",
         "why": "the boundary between levels is destroyed",
         "symptom": "levels merging into one another"},
        {"mistake": "Using newest-first ordering",
         "why": "that produces depth-first order, not level order",
         "symptom": "correct {unit}s grouped into the wrong levels"},
        {"mistake": "Not handling an empty tree before the first round",
         "why": "the root may not exist",
         "symptom": "a crash or a spurious empty level"},
    ),
    failure_cases=(
        {"mistake": "Measuring the level size after enqueuing the next level",
         "trigger": "any tree deeper than two levels",
         "expected": "one group per level",
         "actual": "levels bleeding together",
         "why": "The count has to be taken at the top of the round, while the pending "
                "group holds exactly one level and nothing else."},
        {"mistake": "Seeding the traversal without checking the root exists",
         "trigger": "an empty tree",
         "expected": "an empty result",
         "actual": "a result containing one empty level, or a crash",
         "why": "Absence of a root is not the same as a level with nothing in it."},
    ),
    edge_cases=(
        "An empty tree",
        "A single {unit}",
        "A tree degenerate into a straight line",
        "A very wide, shallow tree",
    ),
    rewrite_challenges=(
        "Produce the levels bottom-up without reversing at the end.",
        "Return only the rightmost {unit} of each level.",
        "Compare the memory used by this against the depth-first version.",
    ),
))

BST_PROPERTY = register(Archetype(
    key="bst-property",
    name="Exploiting the search-tree ordering",
    summary="Use the ordering invariant to skip entire subtrees.",
    pattern_hint="The ordering guarantee is doing more work than it looks",
    topics=("tree", "binary-search-tree"),
    target_time="O(h)",
    target_space="O(1)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="This is not just a tree — everything left of a {unit} is smaller and "
           "everything right is larger. Compare {goal} against the root. What does "
           "that one comparison eliminate?",
        l2="It eliminates an entire subtree, not one {unit}. Treating this as an "
           "ordinary tree and visiting everything ignores the one guarantee that makes "
           "it special.",
        l3="Each comparison drops roughly half the remaining {unit}s. On a balanced "
           "tree, how does that change the cost compared with visiting all of them?",
        l4="Walk down from the root, comparing at each {unit} and descending only into "
           "the side that can still contain the answer. Some variants also want the "
           "ordered sequence of values, which this tree gives up for free under a "
           "particular traversal order — worth knowing which one.",
    ),
    approaches=(
        ApproachTemplate(
            name="Search the whole tree",
            idea="Visit every {unit}, ignoring the ordering guarantee.",
            time="O(n)", space="O(h)",
        ),
        ApproachTemplate(
            name="Ordered descent",
            idea="Compare at each {unit} and descend into one side only.",
            time="O(h)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Validating only against the immediate parent",
         "why": "the constraint is inherited from every ancestor, not just one",
         "symptom": "invalid trees accepted when a violation is a level down"},
        {"mistake": "Assuming the tree is balanced",
         "why": "a degenerate tree makes the descent linear",
         "symptom": "correct answers with the expected speed-up absent"},
        {"mistake": "Mishandling duplicate values",
         "why": "which side duplicates belong on is a convention the problem sets",
         "symptom": "inconsistent results when values repeat"},
    ),
    failure_cases=(
        {"mistake": "Checking only that each {unit} sits correctly relative to its parent",
         "trigger": "a tree where a deep {unit} violates an ancestor's bound but not "
                    "its parent's",
         "expected": "invalid",
         "actual": "valid",
         "why": "Every {unit} is constrained by a range inherited from all its "
                "ancestors. Carrying that range down is what makes the check correct."},
        {"mistake": "Descending both sides out of habit",
         "trigger": "a large balanced tree",
         "expected": "a descent proportional to the height",
         "actual": "a full traversal",
         "why": "Correct, but it throws away the entire advantage of the structure. "
                "The comparison exists precisely so one side can be skipped."},
    ),
    edge_cases=(
        "An empty tree",
        "A single {unit}",
        "A tree degenerate into a straight line",
        "Duplicate values",
    ),
    rewrite_challenges=(
        "Produce the values in sorted order without any extra storage.",
        "Find the closest value to {goal} rather than an exact match.",
        "State the range invariant each recursive call maintains.",
    ),
))

# --- graphs ------------------------------------------------------------------

GRAPH_TRAVERSAL = register(Archetype(
    key="graph-traversal",
    name="Graph traversal with a visited set",
    summary="Explore reachable nodes exactly once, tracking what has been seen.",
    pattern_hint="Things are connected to each other, possibly in loops",
    topics=("graph", "depth-first-search", "breadth-first-search"),
    target_time="O(V+E)",
    target_space="O(V)",
    brute_time="unbounded",
    ladder=LadderTemplate(
        l1="Unlike a tree, {collection} can loop back on itself. What happens to a "
           "naive traversal that simply follows every connection it finds?",
        l2="It revisits {unit}s forever. So you need to record what you have already "
           "reached. When is the right moment to mark something — when you first see "
           "it, or when you get around to processing it?",
        l3="Marking on discovery rather than on processing is what prevents the same "
           "{unit} being queued several times before it is ever handled. Now: does "
           "{goal} care about the order you explore in?",
        l4="Explore outward from each starting point, marking {unit}s as you discover "
           "them and skipping anything already marked. Every {unit} and every "
           "connection is handled once. If {goal} depends on distance, explore in "
           "order of discovery; if it does not, either order works.",
    ),
    approaches=(
        ApproachTemplate(
            name="Depth-first exploration",
            idea="Follow each connection as far as it goes before backtracking.",
            time="O(V+E)", space="O(V)",
        ),
        ApproachTemplate(
            name="Breadth-first exploration",
            idea="Expand outward evenly, which also yields shortest hop counts.",
            time="O(V+E)", space="O(V)",
        ),
    ),
    pitfalls=(
        {"mistake": "Marking a {unit} when processing rather than when discovering",
         "why": "the same {unit} can be queued many times before being handled",
         "symptom": "correct answers with badly degraded performance"},
        {"mistake": "Only exploring from one starting point",
         "why": "{collection} may be split into disconnected pieces",
         "symptom": "everything beyond the first component missed"},
        {"mistake": "Using depth-first for shortest-path questions",
         "why": "the first route found is not the shortest one",
         "symptom": "a valid path that is longer than necessary"},
    ),
    failure_cases=(
        {"mistake": "Not marking {unit}s as seen at all",
         "trigger": "any {collection} containing a loop",
         "expected": "a terminating traversal",
         "actual": "an infinite loop or stack overflow",
         "why": "Without a record of what has been reached, a cycle is followed "
                "forever. Trees do not need this; graphs always do."},
        {"mistake": "Starting the traversal only from the first {unit}",
         "trigger": "a {collection} in two disconnected pieces",
         "expected": "a result covering both",
         "actual": "a result covering only the piece containing the start",
         "why": "Reachability is not the same as membership. Every unvisited {unit} "
                "has to be considered as a fresh starting point."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A single {unit} with no connections",
        "Several disconnected pieces",
        "A {unit} connected to itself",
    ),
    rewrite_challenges=(
        "Swap depth-first for breadth-first and note what the answer gains or loses.",
        "Count the connected pieces rather than exploring one.",
        "Detect whether a cycle exists during the traversal.",
    ),
))

TOPOLOGICAL_SORT = register(Archetype(
    key="topological-sort",
    name="Topological ordering",
    summary="Order items so every dependency comes before what needs it.",
    pattern_hint="Some things must happen before others",
    topics=("graph", "topological-sort"),
    target_time="O(V+E)",
    target_space="O(V)",
    brute_time="O(V!)",
    ladder=LadderTemplate(
        l1="Every {unit} has things that must come before it. Which {unit}s could you "
           "safely do first, right now, with nothing outstanding?",
        l2="Exactly those with no outstanding prerequisites. Once you complete one, "
           "what changes for the {unit}s that were waiting on it?",
        l3="Their outstanding count drops, and some reach zero and become available. "
           "So the whole process is: take anything available, complete it, release "
           "whatever it unblocks. What tells you the ordering is impossible?",
        l4="Count outstanding prerequisites for every {unit}. Repeatedly take one with "
           "none left, record it, and decrease the counts of everything depending on "
           "it. If you record every {unit}, that order is the answer; if you run out "
           "of available {unit}s early, the remainder contains a cycle.",
    ),
    approaches=(
        ApproachTemplate(
            name="Try every permutation",
            idea="Generate orderings until one satisfies all constraints.",
            time="O(V!)", space="O(V)",
        ),
        ApproachTemplate(
            name="Prerequisite counting",
            idea="Repeatedly take {unit}s with nothing outstanding and release their "
                 "dependents.",
            time="O(V+E)", space="O(V)",
        ),
    ),
    pitfalls=(
        {"mistake": "Building the dependency direction backwards",
         "why": "the arrows encode which side must wait",
         "symptom": "a valid-looking order that is exactly reversed"},
        {"mistake": "Not detecting a cycle",
         "why": "a cyclic input has no valid ordering at all",
         "symptom": "a truncated order returned as if it were complete"},
        {"mistake": "Decreasing counts for the wrong side of the relation",
         "why": "only dependents are released by a completion",
         "symptom": "counts that never reach zero"},
    ),
    failure_cases=(
        {"mistake": "Returning the recorded order without checking its length",
         "trigger": "an input containing a circular dependency",
         "expected": "an explicit impossible result",
         "actual": "a partial order presented as complete",
         "why": "The loop stops when nothing is available, which happens both on "
                "success and on a cycle. Only the count of recorded {unit}s "
                "distinguishes them."},
        {"mistake": "Reversing the direction of the dependency edges",
         "trigger": "any input with a strict ordering requirement",
         "expected": "prerequisites before dependents",
         "actual": "dependents before prerequisites",
         "why": "Both directions produce a clean topological order of *some* graph. "
                "Only one of them is the graph you were given."},
    ),
    edge_cases=(
        "No dependencies at all",
        "A single chain of dependencies",
        "A cycle",
        "Disconnected groups of dependencies",
    ),
    rewrite_challenges=(
        "Detect the cycle and report which {unit}s are involved.",
        "Produce the lexicographically smallest valid order.",
        "Solve it with depth-first traversal instead and compare.",
    ),
))

UNION_FIND = register(Archetype(
    key="union-find",
    name="Disjoint set union",
    summary="Track group membership under repeated merges.",
    pattern_hint="Things are being grouped together as you go",
    topics=("graph", "union-find"),
    target_time="O(n a(n))",
    target_space="O(n)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="{unit}s get merged into groups as you process {collection}. The only two "
           "questions you ever ask are whether two {unit}s share a group, and merge "
           "these two groups. Nothing else.",
        l2="Re-exploring the connections every time you need an answer works but "
           "repeats enormous amounts of work. What if each group simply had a single "
           "designated representative?",
        l3="Then 'same group' becomes 'same representative', and merging is pointing "
           "one representative at the other. The danger is the chains getting long. "
           "What could you do while walking a chain to make later walks shorter?",
        l4="Give every {unit} a parent, initially itself. The representative is found "
           "by following parents to the top. Merging points one top at the other. Two "
           "refinements keep it fast: flatten the chain while walking it, and always "
           "attach the smaller group beneath the larger.",
    ),
    approaches=(
        ApproachTemplate(
            name="Re-traverse for each query",
            idea="Explore {collection} from scratch whenever membership is asked.",
            time="O(n^2)", space="O(n)",
        ),
        ApproachTemplate(
            name="Disjoint set with flattening",
            idea="Maintain a representative per group, flattening chains as you find "
                 "them.",
            time="O(n a(n))", space="O(n)",
        ),
    ),
    pitfalls=(
        {"mistake": "Merging the {unit}s rather than their representatives",
         "why": "it links two members without joining the groups",
         "symptom": "groups that appear separate despite being merged"},
        {"mistake": "Skipping both flattening and size-based attachment",
         "why": "chains degenerate into long lists",
         "symptom": "correct answers that slow to a crawl on large inputs"},
        {"mistake": "Counting groups by counting merges",
         "why": "a merge of two already-joined {unit}s changes nothing",
         "symptom": "an undercount of the remaining groups"},
    ),
    failure_cases=(
        {"mistake": "Pointing one {unit} at another instead of one root at another",
         "trigger": "three {unit}s merged in two separate operations",
         "expected": "a single group of three",
         "actual": "two groups",
         "why": "Attaching a member rather than its representative leaves the rest of "
                "its group behind, still pointing at the old root."},
        {"mistake": "Decrementing the group count on every merge request",
         "trigger": "the same pair merged twice",
         "expected": "the count reduced once",
         "actual": "the count reduced twice",
         "why": "A merge only reduces the number of groups when the two were actually "
                "distinct. The representatives have to be compared first."},
    ),
    edge_cases=(
        "No merges at all",
        "Every {unit} merged into one group",
        "The same pair merged repeatedly",
        "A {unit} merged with itself",
    ),
    rewrite_challenges=(
        "Track the size of each group as merges happen.",
        "Solve the same problem with a traversal and compare the complexity.",
        "Explain why flattening makes the amortised cost nearly constant.",
    ),
))

# --- backtracking ------------------------------------------------------------

BACKTRACKING = register(Archetype(
    key="backtracking",
    name="Backtracking search",
    summary="Build candidates incrementally and abandon them the moment they fail.",
    pattern_hint="You are being asked to produce arrangements, not compute a value",
    topics=("backtracking", "recursion"),
    target_time="O(branching^depth)",
    target_space="O(depth)",
    brute_time="O(branching^depth)",
    ladder=LadderTemplate(
        l1="{goal} asks for arrangements rather than a single number, so something "
           "exponential is unavoidable. The question is only how much of the search "
           "space you can avoid touching.",
        l2="Think of building one candidate step by step. At each step you choose from "
           "a set of options. What makes an option illegal given what you have already "
           "chosen?",
        l3="If you can detect illegality as soon as it appears, you never explore "
           "anything beneath it. That pruning is the whole difference between "
           "unusable and fast enough.",
        l4="Extend a partial candidate one choice at a time. When it is complete, "
           "record it. When it becomes impossible, abandon it immediately. After "
           "exploring a choice, undo it before trying the next — the state you carry "
           "must look exactly as it did before that choice was made.",
    ),
    approaches=(
        ApproachTemplate(
            name="Generate then filter",
            idea="Produce every arrangement and discard the invalid ones.",
            time="O(branching^depth)", space="O(branching^depth)",
        ),
        ApproachTemplate(
            name="Backtracking with pruning",
            idea="Abandon partial candidates as soon as they cannot succeed.",
            time="much less in practice", space="O(depth)",
        ),
    ),
    pitfalls=(
        {"mistake": "Not undoing a choice after exploring it",
         "why": "later branches inherit state they never chose",
         "symptom": "results containing impossible combinations"},
        {"mistake": "Recording a reference to the working candidate",
         "why": "it keeps mutating after being recorded",
         "symptom": "every recorded result identical, often empty"},
        {"mistake": "Checking validity only when a candidate is complete",
         "why": "the entire subtree beneath an invalid prefix is explored for nothing",
         "symptom": "correct results, catastrophic running time"},
    ),
    failure_cases=(
        {"mistake": "Storing the working candidate rather than a copy of it",
         "trigger": "any input producing more than one arrangement",
         "expected": "the distinct arrangements",
         "actual": "several identical entries, usually empty",
         "why": "Every recorded entry points at the same mutable object, which the "
                "search continues to modify and eventually unwinds to empty."},
        {"mistake": "Forgetting to undo the choice on the way back up",
         "trigger": "any input with more than one option at the first step",
         "expected": "arrangements built from independent choices",
         "actual": "arrangements accumulating choices from sibling branches",
         "why": "Each branch must start from exactly the state its parent had. "
                "Undoing is what restores that."},
    ),
    edge_cases=(
        "An empty input",
        "A single option",
        "Duplicate options requiring deduplication",
        "An input where no valid arrangement exists",
    ),
    rewrite_challenges=(
        "Count the arrangements without materialising any of them.",
        "Add one more pruning rule and measure what it saves.",
        "Return only the first valid arrangement and stop.",
    ),
))

# --- dynamic programming -----------------------------------------------------

DP_LINEAR = register(Archetype(
    key="dp-linear",
    name="One-dimensional dynamic programming",
    summary="Each position's answer is built from a few earlier positions.",
    pattern_hint="The answer here seems to depend on the answers just before it",
    topics=("dynamic-programming", "array"),
    target_time="O(n)",
    target_space="O(n)",
    brute_time="O(2^n)",
    ladder=LadderTemplate(
        l1="Stand at one position in {collection} and assume every earlier position "
           "already has its correct answer. Can you work out the answer here from "
           "those?",
        l2="Say precisely which earlier positions you need — often just the previous "
           "one or two. That relationship is the problem; everything after it is "
           "bookkeeping.",
        l3="Recursion expressing that relationship directly recomputes the same "
           "positions enormously often. What would change if each position's answer "
           "were computed once and kept?",
        l4="Work forwards, filling in each position from the earlier ones your rule "
           "names, after settling the first position or two by hand. If the rule only "
           "reaches back a fixed distance, you do not need to keep the whole table — "
           "only that many recent values.",
    ),
    approaches=(
        ApproachTemplate(
            name="Plain recursion",
            idea="Express the relationship directly and recompute freely.",
            time="O(2^n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Tabulation",
            idea="Fill positions in order, each from the earlier ones it depends on.",
            time="O(n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Rolling values",
            idea="Keep only the few recent answers the rule actually reaches back to.",
            time="O(n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Wrong or missing base cases",
         "why": "every later position inherits the error",
         "symptom": "answers off by a constant everywhere"},
        {"mistake": "Filling positions in an order that reads unwritten entries",
         "why": "a dependency must be computed before its dependent",
         "symptom": "answers built from default values"},
        {"mistake": "Reducing to rolling values without checking the reach",
         "why": "the rule may look back further than you kept",
         "symptom": "correct on small inputs, wrong on larger ones"},
    ),
    failure_cases=(
        {"mistake": "Initialising the table to zero and treating that as computed",
         "trigger": "an input whose true answer at some position is zero",
         "expected": "the correct answer",
         "actual": "an answer that silently used an uncomputed entry",
         "why": "Zero means both not-yet-computed and legitimately zero. Those need "
                "to be distinguishable, or the base cases need to be explicit."},
        {"mistake": "Keeping only the previous value when the rule reaches back two",
         "trigger": "any input long enough for the second-back dependency to matter",
         "expected": "the correct answer",
         "actual": "an answer that drifts as the input grows",
         "why": "The space reduction is only valid up to the rule's actual reach. "
                "Check the recurrence before collapsing the table."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A single {unit}",
        "Exactly two {unit}s",
        "All values identical",
    ),
    rewrite_challenges=(
        "Reduce the memory to a constant number of values, and justify why it is safe.",
        "Reconstruct the choice sequence that produced the answer, not just its value.",
        "Write the same solution top-down with memoisation and compare.",
    ),
))

DP_GRID = register(Archetype(
    key="dp-grid",
    name="Two-dimensional dynamic programming",
    summary="Each cell's answer is built from its neighbours in a fixed direction.",
    pattern_hint="Two things are varying at once",
    topics=("dynamic-programming", "matrix"),
    target_time="O(n*m)",
    target_space="O(n*m)",
    brute_time="O(2^(n+m))",
    ladder=LadderTemplate(
        l1="The state here needs two numbers to describe, not one. Name them before "
           "anything else: what exactly does an answer at a given pair of positions "
           "mean?",
        l2="With that definition fixed, which neighbouring states does a cell depend "
           "on? Usually a small, fixed set — directly above, directly left, or "
           "diagonally back.",
        l3="Those dependencies dictate the order you must fill the table in: every "
           "cell a value depends on must already be settled when you reach it. Which "
           "traversal order guarantees that?",
        l4="Settle the first row and column by hand, then fill the table in an order "
           "respecting the dependencies, each cell combining the neighbours your rule "
           "names. If each row only depends on the one above it, a single row of "
           "storage is enough.",
    ),
    approaches=(
        ApproachTemplate(
            name="Exhaustive recursion",
            idea="Explore every route through the two dimensions.",
            time="O(2^(n+m))", space="O(n+m)",
        ),
        ApproachTemplate(
            name="Full table",
            idea="Fill every cell once from its settled neighbours.",
            time="O(n*m)", space="O(n*m)",
        ),
        ApproachTemplate(
            name="Rolling row",
            idea="Keep one row when the rule only reaches the previous row.",
            time="O(n*m)", space="O(m)",
        ),
    ),
    pitfalls=(
        {"mistake": "An imprecise definition of what a cell means",
         "why": "every subsequent decision depends on that definition",
         "symptom": "a recurrence that almost works"},
        {"mistake": "Filling in an order that violates the dependencies",
         "why": "cells get built from unsettled neighbours",
         "symptom": "answers that change if the loop order is swapped"},
        {"mistake": "Getting the first row or column wrong",
         "why": "boundary cells have fewer neighbours",
         "symptom": "errors concentrated along one edge"},
    ),
    failure_cases=(
        {"mistake": "Overwriting a row in place when the rule needs the old value",
         "trigger": "any input where a cell depends on the diagonal",
         "expected": "the correct answer",
         "actual": "an answer using this row's already-updated value",
         "why": "Collapsing to one row is only safe if you never need a value the "
                "update has already destroyed. The diagonal is exactly that value."},
        {"mistake": "Treating the boundary as if it had all its neighbours",
         "trigger": "any input, visible immediately in the first row",
         "expected": "boundary cells computed from their base definition",
         "actual": "out-of-range access or garbage along the edge",
         "why": "The first row and column have no predecessors in one direction. They "
                "are base cases, not general cases."},
    ),
    edge_cases=(
        "One of the dimensions being zero",
        "A single row or a single column",
        "A one-by-one input",
        "Both dimensions at their maximum",
    ),
    rewrite_challenges=(
        "Reduce the storage to a single row and explain why it remains correct.",
        "Reconstruct the actual path or sequence, not just the value.",
        "State in one sentence what a cell means, precisely enough to test.",
    ),
))

# --- prefix sums -------------------------------------------------------------

PREFIX_SUM = register(Archetype(
    key="prefix-sum",
    name="Prefix accumulation",
    summary="Precompute running totals so any range is answerable in one step.",
    pattern_hint="The same stretches of data are being totalled over and over",
    topics=("array", "prefix-sum"),
    target_time="O(n)",
    target_space="O(n)",
    brute_time="O(n^2)",
    ladder=LadderTemplate(
        l1="You keep needing the total over stretches of {collection}. Two overlapping "
           "stretches share almost all their {unit}s — how much of that work are you "
           "currently repeating?",
        l2="If you knew the running total from the start up to any position, could you "
           "get the total of an arbitrary stretch without touching its interior?",
        l3="Yes — the difference of two running totals. That turns a range question "
           "into a subtraction. What does it cost to have every running total "
           "available?",
        l4="Build the running totals in one pass. Any stretch is then the difference "
           "between the total at its end and the total just before its start. That "
           "off-by-one at the start is where most of the bugs in this pattern live.",
    ),
    approaches=(
        ApproachTemplate(
            name="Re-sum each range",
            idea="Total the {unit}s of every stretch directly.",
            time="O(n^2)", space="O(1)",
        ),
        ApproachTemplate(
            name="Prefix totals",
            idea="Precompute running totals and answer each range by subtraction.",
            time="O(n)", space="O(n)",
        ),
    ),
    pitfalls=(
        {"mistake": "Subtracting the wrong boundary",
         "why": "the start of the range must be excluded, not included",
         "symptom": "answers off by exactly one {unit}"},
        {"mistake": "No leading zero in the totals",
         "why": "ranges starting at the beginning have nothing to subtract",
         "symptom": "out-of-range access or a wrong first answer"},
        {"mistake": "Assuming values are non-negative",
         "why": "some variants rely on totals being monotonic",
         "symptom": "correct on positive input, wrong with negatives"},
    ),
    failure_cases=(
        {"mistake": "Indexing the running totals without a leading zero entry",
         "trigger": "a range starting at the very first {unit}",
         "expected": "the total of that range",
         "actual": "an out-of-range access, or a total missing its first {unit}",
         "why": "The subtraction needs the total *before* the range starts. For a "
                "range at position zero that value is zero, and it has to exist."},
        {"mistake": "Assuming a sliding window works because the values look positive",
         "trigger": "an input containing negative values",
         "expected": "the correct range",
         "actual": "a missed answer",
         "why": "Window shrinking assumes extending a range cannot help once it is "
                "too large. Negative values break that, which is what pushes these "
                "problems toward prefix totals plus a lookup structure."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A range covering everything",
        "A range of a single {unit}",
        "Negative values and zeroes",
    ),
    rewrite_challenges=(
        "Support updates to {collection} between range queries.",
        "Extend it to two dimensions.",
        "Count the ranges summing to {goal} using a lookup structure alongside.",
    ),
))

# --- greedy ------------------------------------------------------------------

GREEDY = register(Archetype(
    key="greedy",
    name="Greedy choice",
    summary="A locally best choice that provably leads to a globally best answer.",
    pattern_hint="The obvious move at each step may simply be correct",
    topics=("greedy", "array"),
    target_time="O(n log n)",
    target_space="O(1)",
    brute_time="O(2^n)",
    ladder=LadderTemplate(
        l1="Consider the most obviously attractive move at the current step. Write "
           "down what makes it attractive — that criterion is the candidate rule.",
        l2="Now try to break it. Construct an input where taking that move makes the "
           "final answer worse. If you cannot, you may have a valid rule; if you can, "
           "the rule needs changing, not patching.",
        l3="A greedy rule is only correct if taking it never rules out an optimal "
           "answer. Many of these problems also need {collection} in a particular "
           "order before the rule is even meaningful. Which order?",
        l4="Order {collection} by the criterion your rule depends on, then sweep "
           "through making the locally best choice each time, carrying only the small "
           "amount of state the rule needs. If you cannot justify why the rule never "
           "costs you the optimum, the problem probably wants dynamic programming.",
    ),
    approaches=(
        ApproachTemplate(
            name="Explore every combination",
            idea="Try all sequences of choices and keep the best.",
            time="O(2^n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Sort and take the best local choice",
            idea="Order by the deciding criterion and sweep once.",
            time="O(n log n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Assuming greedy works without an argument",
         "why": "many problems that look greedy are not",
         "symptom": "passing the samples, failing a mid-sized case"},
        {"mistake": "Sorting by the wrong criterion",
         "why": "the rule is only valid under one particular order",
         "symptom": "answers close to optimal but not optimal"},
        {"mistake": "Tracking more state than the rule needs",
         "why": "it usually signals the rule is not actually greedy",
         "symptom": "code that grows complicated without becoming correct"},
    ),
    failure_cases=(
        {"mistake": "Taking the largest available option at every step",
         "trigger": "an input where a smaller early choice unlocks two better later ones",
         "expected": "the optimal total",
         "actual": "a total that is locally best at every step and globally worse",
         "why": "Greedy is a claim about the future, not the present. Without an "
                "argument that the choice never forecloses an optimum, it is a guess."},
        {"mistake": "Sorting by one endpoint when the rule depends on the other",
         "trigger": "an input containing one very wide item and several narrow ones",
         "expected": "the maximum number of compatible choices",
         "actual": "one fewer",
         "why": "The wide item is attractive under the wrong ordering and blocks "
                "several others. Which endpoint you sort by *is* the algorithm."},
    ),
    edge_cases=(
        "An empty {collection}",
        "A single option",
        "All options identical",
        "Options that all conflict with one another",
    ),
    rewrite_challenges=(
        "Write the exhaustive version and check the greedy answer against it on random inputs.",
        "State the exchange argument justifying the rule.",
        "Find an input where the obvious greedy rule fails, if one exists.",
    ),
))

# --- bit manipulation --------------------------------------------------------

BIT_MANIPULATION = register(Archetype(
    key="bit-manipulation",
    name="Bitwise reasoning",
    summary="Treat numbers as fixed-width bit patterns rather than quantities.",
    pattern_hint="The binary representation may matter more than the value",
    topics=("bit-manipulation", "math"),
    target_time="O(n)",
    target_space="O(1)",
    brute_time="O(n log n)",
    ladder=LadderTemplate(
        l1="Stop thinking of these as quantities for a moment and think of them as "
           "rows of bits. Looking at a single bit position across all of {collection}, "
           "what do you notice?",
        l2="Each bit position is independent of the others. That means you can reason "
           "about one column at a time and never worry about carrying.",
        l3="There are operations that combine two numbers bit by bit — one that cancels "
           "matching bits, one that keeps only shared bits, one that keeps bits present "
           "in either. Which of those matches {goal}?",
        l4="Combine {collection} with the operation whose behaviour matches {goal}, "
           "column by column. The properties that make this work are that order does "
           "not matter and that the operation undoes itself, so anything appearing an "
           "even number of times disappears on its own.",
    ),
    approaches=(
        ApproachTemplate(
            name="Count occurrences",
            idea="Tally every value and inspect the counts.",
            time="O(n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Bitwise combination",
            idea="Fold {collection} with a bitwise operation, using constant space.",
            time="O(n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Ignoring negative numbers and sign extension",
         "why": "shifting a negative value is language-dependent",
         "symptom": "correct on positives, wrong or looping on negatives"},
        {"mistake": "Assuming a fixed width that the language does not have",
         "why": "some languages use arbitrary-precision integers",
         "symptom": "an infinite loop when shifting"},
        {"mistake": "Confusing the operators",
         "why": "cancelling, intersecting and unioning bits are different operations",
         "symptom": "an answer that is right only when the input is tiny"},
    ),
    failure_cases=(
        {"mistake": "Shifting right in a loop on a negative value",
         "trigger": "any negative {unit}",
         "expected": "termination after the width of the number",
         "actual": "an infinite loop",
         "why": "Sign extension keeps feeding in set bits from the left, so the value "
                "never reaches zero. The loop needs a bounded count, not a zero test."},
        {"mistake": "Using the operation that keeps shared bits when you need the one "
                    "that cancels them",
         "trigger": "a {collection} where every value but one appears twice",
         "expected": "the value appearing once",
         "actual": "zero, or an unrelated value",
         "why": "Only the cancelling operation makes pairs vanish. Keeping shared bits "
                "collapses toward zero as soon as any two values differ."},
    ),
    edge_cases=(
        "A single {unit}",
        "Zero as a value",
        "Negative values",
        "Values at the maximum width",
    ),
    rewrite_challenges=(
        "Solve it with a counting structure and compare the space used.",
        "Handle the variant where values repeat three times rather than twice.",
        "Explain why order of combination does not affect the result.",
    ),
))

# --- tries -------------------------------------------------------------------

TRIE = register(Archetype(
    key="trie",
    name="Prefix tree",
    summary="Share common prefixes so lookups cost the length of the key.",
    pattern_hint="Many of these keys begin the same way",
    topics=("trie", "string", "design"),
    target_time="O(L)",
    target_space="O(total characters)",
    brute_time="O(n*L)",
    ladder=LadderTemplate(
        l1="Look at {collection} and notice how much the keys have in common at their "
           "starts. Storing each key separately stores those shared beginnings over "
           "and over.",
        l2="What if the shared beginning were stored once, with the keys diverging only "
           "where they actually differ? What shape does that structure take?",
        l3="A tree where each step consumes one character and each path spells a "
           "prefix. Looking up a key then costs its own length, regardless of how many "
           "keys exist. What extra information does a node need so you can tell a "
           "complete key from a mere prefix?",
        l4="Build a tree whose edges are characters. Inserting walks down, creating "
           "steps as needed, and marks the final node as terminal. Searching walks the "
           "same path and checks that mark. Prefix queries are identical but skip the "
           "terminal check — that one flag is the whole difference.",
    ),
    approaches=(
        ApproachTemplate(
            name="Check every key",
            idea="Compare against each stored key in turn.",
            time="O(n*L)", space="O(n*L)",
        ),
        ApproachTemplate(
            name="Prefix tree",
            idea="Share prefixes structurally so lookup costs only the key length.",
            time="O(L)", space="O(total characters)",
        ),
    ),
    pitfalls=(
        {"mistake": "No terminal marker on nodes",
         "why": "a stored prefix becomes indistinguishable from a stored key",
         "symptom": "prefixes of real keys reported as present"},
        {"mistake": "Sharing one child map across nodes",
         "why": "a mutable default is created once, not per node",
         "symptom": "every key appearing to contain every other"},
        {"mistake": "Not handling the empty key",
         "why": "it terminates at the root",
         "symptom": "an incorrect answer or a crash on empty input"},
    ),
    failure_cases=(
        {"mistake": "Reporting a key as present whenever its path exists",
         "trigger": "searching for a string that is a strict prefix of a stored key",
         "expected": "not present",
         "actual": "present",
         "why": "The path exists because a longer key created it. Only the terminal "
                "marker distinguishes a stored key from a waypoint."},
        {"mistake": "Giving every node the same child mapping by accident",
         "trigger": "inserting two keys with different first characters",
         "expected": "two separate branches",
         "actual": "both keys appearing under every branch",
         "why": "A shared mutable default means every node writes into one object. "
                "Each node needs its own."},
    ),
    edge_cases=(
        "An empty key",
        "One key that is a prefix of another",
        "Keys with no shared prefix at all",
        "A single very long key",
    ),
    rewrite_challenges=(
        "Support deletion, freeing nodes no key needs any more.",
        "Add wildcard matching for a single character.",
        "Compare the memory against a plain hash set, honestly.",
    ),
))

# --- matrix ------------------------------------------------------------------

MATRIX_TRAVERSAL = register(Archetype(
    key="matrix-traversal",
    name="Matrix walking and transformation",
    summary="Index arithmetic over a grid, often in place.",
    pattern_hint="The indices themselves are the puzzle",
    topics=("matrix", "array", "simulation"),
    target_time="O(n*m)",
    target_space="O(1)",
    brute_time="O(n*m)",
    ladder=LadderTemplate(
        l1="Take a small grid and write out, by hand, where each {unit} needs to end "
           "up. Do not generalise yet — just get the mapping down for a three-by-three.",
        l2="Look at the pairs of original and final positions you wrote down. What is "
           "the relationship between the two, expressed in terms of the row, the "
           "column, and the size?",
        l3="Building a fresh grid from that mapping is straightforward. Doing it in "
           "place is harder, because writing one position destroys another. What has "
           "to happen to the displaced value?",
        l4="Either construct the result separately from the mapping, or, for in place, "
           "move values in closed cycles so nothing is lost — often achievable as a "
           "sequence of simpler whole-grid operations rather than one clever pass.",
    ),
    approaches=(
        ApproachTemplate(
            name="Build a new grid",
            idea="Write each {unit} into a fresh grid at its mapped position.",
            time="O(n*m)", space="O(n*m)",
        ),
        ApproachTemplate(
            name="In-place transformation",
            idea="Move values in cycles, or compose simpler whole-grid operations.",
            time="O(n*m)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Confusing rows with columns",
         "why": "the two index orders are easy to transpose mentally",
         "symptom": "a transposed or mirrored result"},
        {"mistake": "Overwriting a value before it has been moved",
         "why": "in-place work destroys as it writes",
         "symptom": "duplicated values and lost ones"},
        {"mistake": "Assuming the grid is square",
         "why": "many transformations only make sense when it is",
         "symptom": "out-of-range access on rectangular input"},
    ),
    failure_cases=(
        {"mistake": "Writing directly into the target position without saving what was there",
         "trigger": "any grid larger than one by one",
         "expected": "every {unit} relocated",
         "actual": "one value smeared across several positions",
         "why": "Each write destroys a value that had not moved yet. Either move in "
                "complete cycles or work into separate storage."},
        {"mistake": "Iterating the full grid while transforming in place",
         "trigger": "a square grid being rotated by layers",
         "expected": "one rotation",
         "actual": "values rotated twice, landing back near where they started",
         "why": "Covering every position revisits cells that have already been moved. "
                "The traversal must cover each cycle exactly once."},
    ),
    edge_cases=(
        "An empty grid",
        "A one-by-one grid",
        "A single row or single column",
        "A rectangular, non-square grid",
    ),
    rewrite_challenges=(
        "Do it in place using a constant amount of extra space.",
        "Handle rectangular grids, or explain precisely why you cannot.",
        "Express the transformation as a composition of two simpler ones.",
    ),
))

# --- in-place array marking --------------------------------------------------

INDEX_AS_STORAGE = register(Archetype(
    key="index-as-storage",
    name="Using the array itself as storage",
    summary="Encode information in positions or signs to reach constant extra space.",
    pattern_hint="The constraints on the values look suspiciously like the indices",
    topics=("array", "in-place"),
    target_time="O(n)",
    target_space="O(1)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="Read the constraints on the values in {collection} and compare them with "
           "the valid positions. That correspondence is not a coincidence.",
        l2="A lookup structure solves this immediately but costs space proportional to "
           "the input. You are being asked for constant extra space, so the "
           "information has to live somewhere that already exists.",
        l3="{collection} itself is writable. Is there a way to record 'I have seen the "
           "value that belongs at this position' without losing the value stored "
           "there?",
        l4="Use each position as its own marker — either by moving values to where "
           "they belong, or by marking the position a value points at while keeping "
           "enough information to recover the original. Then a second pass reads the "
           "answer off the positions that were never marked.",
    ),
    approaches=(
        ApproachTemplate(
            name="Auxiliary lookup structure",
            idea="Record seen values in a separate set or map.",
            time="O(n)", space="O(n)",
        ),
        ApproachTemplate(
            name="In-place marking",
            idea="Encode the information in {collection} itself and read it back in a "
                 "second pass.",
            time="O(n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Destroying values you still need",
         "why": "the marking must be reversible or non-destructive",
         "symptom": "correct on the first pass, wrong on the second"},
        {"mistake": "Marking the same position twice",
         "why": "a repeated mark can undo itself",
         "symptom": "duplicates in the input producing wrong answers"},
        {"mistake": "Not handling values outside the valid range",
         "why": "they index nothing and must be neutralised first",
         "symptom": "out-of-range access"},
    ),
    failure_cases=(
        {"mistake": "Negating a position that was already negated",
         "trigger": "a {collection} containing the same value twice",
         "expected": "the position stays marked",
         "actual": "the mark is undone",
         "why": "Negation is its own inverse. Marking must check whether the mark is "
                "already present rather than blindly toggling."},
        {"mistake": "Indexing with a value outside the valid range",
         "trigger": "a {collection} containing a value larger than its length",
         "expected": "that value ignored",
         "actual": "an out-of-range access",
         "why": "Only values that correspond to positions can be used as positions. "
                "Everything else has to be filtered or clamped first."},
    ),
    edge_cases=(
        "An empty {collection}",
        "All values identical",
        "Values outside the valid range",
        "An already-correct arrangement",
    ),
    rewrite_challenges=(
        "Restore {collection} to its original state afterwards.",
        "Solve it with a lookup structure and compare readability against space.",
        "Handle values outside the range explicitly rather than assuming them away.",
    ),
))

# --- design ------------------------------------------------------------------

DESIGN_COMPOSITE = register(Archetype(
    key="design-composite",
    name="Composing two structures for one guarantee",
    summary="No single structure gives every required operation the needed cost.",
    pattern_hint="Each operation is easy alone; together they conflict",
    topics=("design", "hash-table", "linked-list"),
    target_time="O(1)",
    target_space="O(n)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="List the operations you must support and the cost each is allowed. Then "
           "pick your favourite single structure and mark which of those it fails.",
        l2="Every single structure fails at least one. That is the actual problem: no "
           "one of them provides all the guarantees at once.",
        l3="So use two, each covering the other's weakness, kept perfectly in step. "
           "Which structure gives instant lookup by key, and which gives instant "
           "insertion and removal at arbitrary positions?",
        l4="Combine a lookup structure mapping keys to locations with an ordered "
           "structure supporting cheap rearrangement. Every operation touches both, "
           "and the correctness hinges entirely on their never disagreeing about what "
           "exists.",
    ),
    approaches=(
        ApproachTemplate(
            name="Single structure",
            idea="Use one structure and accept a linear cost on some operation.",
            time="O(n)", space="O(n)",
        ),
        ApproachTemplate(
            name="Two structures kept in step",
            idea="Pair fast lookup with cheap reordering, updating both together.",
            time="O(1)", space="O(n)",
        ),
    ),
    pitfalls=(
        {"mistake": "Updating one structure and not the other",
         "why": "they encode the same facts and must agree",
         "symptom": "entries that exist in one view and not the other"},
        {"mistake": "Not handling a key that already exists",
         "why": "insert and update are different operations",
         "symptom": "duplicates, or a size that drifts upward"},
        {"mistake": "Missing boundary cases at the ends",
         "why": "removing the first or last element touches fewer links",
         "symptom": "crashes only when the structure empties or holds one item"},
    ),
    failure_cases=(
        {"mistake": "Removing from the ordered structure but leaving the key in the map",
         "trigger": "an eviction followed by a lookup of the evicted key",
         "expected": "not found",
         "actual": "a reference to a removed location",
         "why": "The two structures have diverged. Every mutation must touch both, "
                "which is why these are usually written as a single private helper."},
        {"mistake": "Treating a repeat insertion as a new entry",
         "trigger": "inserting an existing key with a new value",
         "expected": "the entry updated and moved",
         "actual": "two entries for one key",
         "why": "Presence has to be checked first; update and insert follow different "
                "paths through both structures."},
    ),
    edge_cases=(
        "An empty structure",
        "A capacity of one",
        "Repeated keys",
        "Removing the only remaining entry",
    ),
    rewrite_challenges=(
        "Support a capacity supplied at construction, evicting correctly when full.",
        "Make every mutation go through one private helper that touches both structures.",
        "Argue why each operation really is constant time, including the worst case.",
    ),
))

# --- math --------------------------------------------------------------------

MATH_REASONING = register(Archetype(
    key="math-reasoning",
    name="Arithmetic and number-theoretic reasoning",
    summary="A property of the numbers replaces the search entirely.",
    pattern_hint="There may be a closed-form shortcut hiding here",
    topics=("math",),
    target_time="O(log n)",
    target_space="O(1)",
    brute_time="O(n)",
    ladder=LadderTemplate(
        l1="Work the first several cases out by hand and write the results in a row. "
           "Do not look for an algorithm yet — look at the sequence you produced.",
        l2="Is there a relationship between consecutive results, or a closed form that "
           "produces them? Many of these problems are a search only until you notice "
           "the pattern.",
        l3="If a relationship exists, the loop over every value becomes unnecessary. "
           "What remains is arithmetic, and the only real risks are overflow and the "
           "boundaries.",
        l4="Derive the relationship from the small cases, verify it against a case you "
           "did not use to derive it, then implement the arithmetic directly. Handle "
           "zero, one, and negative inputs deliberately — closed forms tend to be "
           "wrong exactly there.",
    ),
    approaches=(
        ApproachTemplate(
            name="Simulate every step",
            idea="Loop through all values and compute directly.",
            time="O(n)", space="O(1)",
        ),
        ApproachTemplate(
            name="Closed form or fast exponentiation",
            idea="Replace the loop with the derived relationship.",
            time="O(log n)", space="O(1)",
        ),
    ),
    pitfalls=(
        {"mistake": "Overflow in an intermediate value",
         "why": "the result fits but a step along the way does not",
         "symptom": "wrong answers only on large inputs"},
        {"mistake": "Deriving a rule from too few cases",
         "why": "several formulas agree on the first three values",
         "symptom": "correct on the samples, wrong beyond them"},
        {"mistake": "Ignoring zero and negative inputs",
         "why": "closed forms often assume a positive domain",
         "symptom": "a crash or nonsense at the boundaries"},
    ),
    failure_cases=(
        {"mistake": "Verifying the derived rule only on the cases it was derived from",
         "trigger": "an input beyond the range you worked out by hand",
         "expected": "the correct value",
         "actual": "a plausible but wrong value",
         "why": "A rule fitted to three points will fit those three points. Confirming "
                "it needs a case that had no say in producing it."},
        {"mistake": "Computing a large intermediate before reducing it",
         "trigger": "an input near the stated constraint limit",
         "expected": "the correct value",
         "actual": "a wrapped or truncated value",
         "why": "The final answer fitting the type does not mean every step did. "
                "Reduce as you go rather than at the end."},
    ),
    edge_cases=(
        "Zero",
        "One",
        "Negative input",
        "The maximum value the constraints allow",
    ),
    rewrite_challenges=(
        "Verify the closed form against a brute-force loop on many random inputs.",
        "Handle the negative domain explicitly.",
        "Prove the relationship rather than inferring it from examples.",
    ),
))
