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
