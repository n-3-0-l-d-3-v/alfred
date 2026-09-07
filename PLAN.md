# Alfred — Architecture & Development Plan

> Status as of 2026-07-22. Working dir `Desktop/Neil/leetLearn` is empty; the prior
> work lives in `Desktop/Neil/codeReview` (git repo, branch `master`, 3 commits).

---

## 1. What actually exists today

The `codeReview` repo ("Chaotic Code Mentor") is **370 lines of Python across 5 files**,
plus 132 lines of tests. Here is the honest inventory:

| File | Lines | What it really does |
|---|---|---|
| `app/main.py` | 25 | One FastAPI endpoint, `POST /analyze`. No auth, no DB, no CORS. |
| `app/analyzer.py` | 79 | Walks Python `ast`. Counts loops, collects variable names, detects exactly 2 patterns. |
| `app/misconceptions.py` | 28 | A hardcoded 2-entry dict mapping pattern → issue/reason/suggestion. |
| `app/solution_engine.py` | 45 | **Returns the same two hardcoded fake solutions regardless of input.** The OpenAI call is a commented-out placeholder. |
| `app/teaching_engine.py` | 61 | If/else chain producing hand-written strings for 2 patterns × 2 levels. |
| `app/test_analyzer.py` | 132 | 11 tests, all green. Genuinely good coverage of what's there. |

**What works:** the AST walker is correct and well-tested. The layering
(analyze → detect → teach) is a sensible skeleton. The test discipline is above
average for a project this size.

**What does not exist at all:**

- No LLM integration. Zero. `generate_solutions()` ignores its `code` argument.
- No browser extension, no frontend, no UI of any kind.
- No database, no user accounts, no persistence between requests.
- No hints, no hint ladder, no gamification, no streaks, no memes.
- No Docker despite the résumé line claiming it.
- Python-only. LeetCode users write C++, Java, JS, Go — the analyzer 500s on all of them.
- Only 2 detectable patterns, both hardcoded.

### The résumé/reality gap

The blurb reads: *"compiler-inspired system that parses code with AST analysis,
detects inefficient problem-solving patterns and misconceptions, generates multiple
optimized solutions with complexity comparison, and delivers personalized teaching
feedback with emotion-aware meme responses — Python · FastAPI · AST · OpenAI API ·
React · Docker."*

Of that: AST analysis is real (2 patterns). FastAPI is real. **OpenAI, React, Docker,
"generates multiple optimized solutions", and "emotion-aware meme responses" describe
software that has not been written.** Fix this by building it — the plan below gets
you to a version where every clause is true by end of Phase 4. Until then, don't
ship that description anywhere it'll be checked.

**Verdict: treat this as greenfield with a reusable 80-line AST module and a good
test harness.** Don't try to grow the current repo into the product; start clean in
`leetLearn/` and port `analyzer.py` in as one component of a much larger system.

---

## 2. Product thesis, and the one rule that makes it work

The pitch: LeetCode gives you almost no support; YouTube drops you into tutorial
hell; AI tools hand you the answer. Alfred sits *between* — it makes you solve it
yourself, then teaches you everything around the solution once you have.

The hard problem is not generating hints. It's **integrity of the hint ladder**. If
the extension can emit a full solution, users escalate straight to level 5 and you've
built a slower ChatGPT. Prompt-begging the model ("don't give the answer") does not
survive contact with a motivated user.

### The AC gate — the structural rule

> **Before a passing submission (pre-AC): Socratic only. The system may never emit
> working solution code for the current problem, at any hint level, under any
> phrasing. After a passing submission (post-AC): the firehose opens.**

Everything follows from this. Pre-AC the model gets a system prompt, a redacted
problem card, and a hard output contract that has no field capable of carrying a
solution. Post-AC it gets a different prompt, the full card, and permission to show
every approach, every wrong turn, every complexity trade-off.

This is what makes the product defensible and honest at the same time — the "AI gives
answers" objection is answered by architecture, not by asking nicely. It also creates
the natural reward loop: solving it yourself is what *unlocks* the good stuff.

Two supporting mechanics:

- **Hints cost something.** A regenerating budget (say 3 hint-tokens/day, +1 per clean
  solve). Escalation is logged and visible: "solved with 4 hints" vs "solved clean."
- **Reviews are always free.** Code review post-AC never costs anything and never
  degrades. That's the part users keep coming back for after they stop needing hints.

---

## 3. Architecture

### 3.1 Surfaces

```
┌─────────────────────────────────────────────────────────────────┐
│  Chrome Extension (MV3)  ── the primary surface                  │
│  ├─ content script on leetcode.com/problems/*                    │
│  │   ├─ DOM adapter: read slug, language, editor buffer, verdict │
│  │   └─ injects sidebar mount point                              │
│  ├─ side panel (React): hints, patterns, review, complexity      │
│  ├─ service worker: auth token, API calls, stuck-detector timers │
│  └─ local cache (IndexedDB): problem cards, offline hint replay  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (JWT)
┌──────────────────────────▼──────────────────────────────────────┐
│  API — FastAPI                                                   │
│  /auth  /session  /hint  /review  /analyze  /progress  /roadmap   │
└───┬──────────────┬──────────────┬───────────────┬───────────────┘
    │              │              │               │
┌───▼───────┐ ┌────▼─────────┐ ┌──▼───────────┐ ┌─▼──────────────┐
│ Static    │ │ LLM layer    │ │ Learner      │ │ Gamification   │
│ analysis  │ │ (Claude)     │ │ model        │ │ engine         │
│ tree-     │ │ prompts +    │ │ mastery,     │ │ streaks, XP,   │
│ sitter    │ │ contracts +  │ │ spaced rep,  │ │ budgets,       │
│ multi-lang│ │ cache        │ │ weak areas   │ │ unlocks        │
└───────────┘ └──────────────┘ └──────────────┘ └────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  Postgres  — users, sessions, submissions, hint_events,          │
│              mastery, streaks, problem_cards (the KB)            │
│  Redis     — rate limits, hint budgets, stuck-detector state     │
│  S3/R2     — meme assets, generated diagrams                     │
└─────────────────────────────────────────────────────────────────┘
                           ▲
┌──────────────────────────┴──────────────────────────────────────┐
│  OFFLINE content pipeline (build-time, not request-time)         │
│  For each problem slug → generate + validate a Problem Card      │
│  via the Batch API. Runs once, refreshed on demand.              │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 The three architectural calls I'd defend

**(a) The AST analyzer is not the core — demote it to a signal provider.**
The current design has AST detection at the center. That's the wrong center: it's
Python-only and it caps out at hand-written pattern rules. The durable assets are
(1) the **problem card knowledge base** and (2) the **learner model**. Static analysis
becomes a cheap, fast grounding signal fed *into* the LLM prompt — loop depth,
recursion present, data structures used, has-memo, mutation-in-loop — which cuts
hallucination and lets you answer "is this O(n²)?" without an API call.

Swap Python's `ast` for **tree-sitter**, which gives you Python, C++, Java, JS, Go, Rust
from one interface with per-language query files. Port the existing `analyzer.py` logic
as the Python query set; it becomes ~1 of 6 grammars rather than the whole system.

**(b) The content pipeline is the real work, and it's offline.**
You cannot hand-write hint ladders for 3,500+ problems, and you must not generate them
per-request (too slow, too expensive, non-deterministic — the same problem would give
different hints to different users). Instead: **generate a Problem Card once per
problem, offline, validate it, store it in Postgres.** Runtime hint serving becomes a
database read with light personalization. This is the single biggest cost and quality
decision in the plan. See §6.

**(c) Keep a platform adapter seam from day one, but don't build the second adapter.**
Define `PlatformAdapter { readProblem(), readCode(), readVerdict(), mount() }` and
implement only `LeetCodeAdapter`. When Codeforces/HackerRank/VS Code come later they
slot in without a rewrite. Costs you a day now; saves a rewrite in Phase 6.

### 3.3 Legal / ToS posture — decide this before Phase 1

LeetCode has no public API and its problem statements are copyrighted. Rules:

- **Read the slug from the URL and the code from the DOM.** That's the user's own
  browser reading a page they're authorized to view.
- **Never store or redistribute LeetCode's problem text.** Your problem cards store
  *your own generated metadata* keyed by slug: pattern tags, hint ladder, complexity
  targets, common-mistake catalog. Generate them from public knowledge of the problem,
  not by scraping and republishing the statement.
- **Don't automate submissions** or anything that looks like traffic they didn't ask for.
- Extension store review will ask about permissions. Request the narrowest host
  permission (`https://leetcode.com/problems/*`), not `<all_urls>`.

---

## 4. Data model (initial)

```
users(id, email, handle, created_at, tz, skill_level, settings_json)
problems(slug PK, title, difficulty, topic_tags[], last_card_build_at)
problem_cards(slug FK, version, patterns_json, hint_ladder_json,
              approaches_json, complexity_json, pitfalls_json,
              edge_cases_json, rewrite_challenges_json, validated_at)
sessions(id, user_id, slug, language, started_at, ended_at,
         solved_at NULL, hints_used, keystrokes, idle_seconds)
submissions(id, session_id, code, verdict, runtime_ms, memory_kb, at)
hint_events(id, session_id, level, source, cost, at)
reviews(id, session_id, model, verdict_json, tone, at)
mastery(user_id, topic, score REAL, confidence, last_seen_at, next_due_at)
streaks(user_id, current, longest, last_active_date, freezes_left)
xp_events(id, user_id, kind, amount, meta_json, at)
```

Notes:
- `problem_cards` is versioned so you can regenerate the KB without breaking history.
- `mastery` doubles as the spaced-repetition table (`next_due_at`) — one table, two jobs.
- `hint_events.source` distinguishes `card` (pre-generated, free) from `llm`
  (personalized, costs a call) so you can measure the cache hit rate that governs unit cost.

---

## 5. Feature catalog

Grouped by when they earn their keep. Phase mapping in §7.

**Core loop (must exist for the product to make sense)**
1. Problem understanding — plain-language restatement, I/O, constraints, analogy
2. Pattern predictor — top-3 patterns with confidence, *without* naming the approach
3. Hint ladder L1–L4 (L5 = full solution, **post-AC only**)
4. Stuck detector — idle time, repeated delete cycles, resubmit-fail loops → offer a hint
5. Post-AC code review — correctness, complexity, readability, idiom
6. Alternative approaches gallery — every reasonable way to solve it, with trade-offs
7. Complexity teaching — not just "O(n²)" but *why*, with the recurrence walked through
8. Wrong-ways gallery — the 5 ways people get this wrong and what each failure looks like

**Progression**
9. Streaks, freezes, daily goal (Duolingo mechanics)
10. XP + levels, clean-solve bonus, hint-penalty
11. Mastery model per topic; hint availability *decreases* as mastery rises
12. Adaptive next-problem recommendation; difficulty escalation on demonstrated mastery
13. Spaced repetition — resurface a solved problem when mastery decays

**Personality**
14. Meme-based review responses (curated asset library, tone-gated — see below)
15. Roast/encourage tone toggle; tone auto-softens on failure streaks

**Depth**
16. Edge-case generator (empty, single, dupes, max constraints, overflow)
17. Rewrite challenges — "now without extra space", "now recursively", "now in O(1) space"
18. Interview mode — the system interrogates you instead of helping
19. "Why did this work?" mode — invariants, correctness argument, proof sketch
20. Contest review mode
21. Analytics dashboard — solved, mastery over time, mistake taxonomy, complexity trend

**Scale-out (Phase 6+)**
22. VS Code extension via the same adapter seam
23. Other judges (Codeforces, HackerRank, AtCoder)
24. Instructor/team mode — cohort mistake analytics
25. System-design mentor

### A note on memes

Do **not** LLM-generate meme images at runtime. Build a curated library of ~60 assets,
each tagged `(situation, intensity)` — e.g. `(nested_loop_on_large_n, medium)`,
`(off_by_one, light)`, `(TLE_after_5_attempts, gentle)`. The model picks a tag; the
backend serves the asset. Reasons: cost, latency, brand safety, and the fact that
generated memes are reliably unfunny.

Tone must be state-aware. A roast after a clean first-try solve lands. The same roast
after four failed submissions and a broken streak reads as cruel and churns the user.
Gate intensity on `(recent_failures, streak_state, user_tone_setting)`.

---

## 6. The LLM layer

Use **Claude**. Model IDs and pricing (current as of this writing):

| Model | ID | In $/MTok | Out $/MTok | Context |
|---|---|---|---|---|
| Opus 4.8 | `claude-opus-4-8` | $5.00 | $25.00 | 1M |
| Haiku 4.5 | `claude-haiku-4-5` | $1.00 | $5.00 | 200K |

Assignment:

- **`claude-opus-4-8`** — offline problem-card generation, post-AC deep code review,
  the "why did this work" explanations. Quality-critical, low frequency.
- **`claude-haiku-4-5`** — high-frequency cheap paths: pattern classification, stuck
  detection triage, complexity sanity checks, meme tag selection. 5× cheaper, plenty
  good for classification.

API details that matter for this build:

- Use `thinking: {type: "adaptive"}` and `output_config: {effort: ...}`. On Opus 4.8 the
  old `budget_tokens` form and `temperature`/`top_p`/`top_k` are **rejected with a 400** —
  don't carry those over from any OpenAI-shaped code.
- Use **structured outputs** (`output_config: {format: {type: "json_schema", schema: ...}}`)
  for every card and every hint response. This is how the AC gate is enforced mechanically:
  the pre-AC schema simply has no field that can hold code.
- Use **prompt caching** on the system prompt + rubric. Cache reads cost ~0.1×.
  ⚠️ On Opus 4.8 the minimum cacheable prefix is **4096 tokens** — a shorter system
  prompt silently won't cache (no error, `cache_creation_input_tokens: 0`). Verify with
  `usage.cache_read_input_tokens` before assuming it's working.
- Use the **Batch API** for the offline pipeline: **50% off**, up to 100k requests per
  batch, most complete within an hour.

### Cost model — do this math before you build the UI

**One-time card generation for the full catalog** (~3,500 problems, ~4K in / ~3K out
each, Opus 4.8 via Batch at 50%):

```
input :  3,500 × 4,000 = 14.0M tok × $5/M  × 0.5 ≈  $ 35
output:  3,500 × 3,000 = 10.5M tok × $25/M × 0.5 ≈  $131
                                            total ≈  $166
```

$166 to build the entire knowledge base, once. That's the cheap part.

**Per-interaction runtime cost** (6K cached system prompt + 3K fresh context + 400 out):

| Path | Opus 4.8 | Haiku 4.5 |
|---|---|---|
| One LLM hint/review call | ≈ $0.028 | ≈ $0.0056 |

At 20 LLM interactions/user/day that's **$0.56/user/day ≈ $17/user/month** on Opus.
That does not survive a free tier. Which is exactly why (b) in §3.2 matters:

> **Most hint serving must be a Postgres read from the pre-generated card, not an LLM
> call.** Target ≥80% card-hit rate. LLM calls are reserved for things that genuinely
> depend on *this user's code*: the post-AC review, misconception diagnosis, and the
> Socratic follow-up when a canned hint didn't land.

Realistic blended target: ~4 LLM calls/active-user/day, mostly Haiku, with a couple of
Opus reviews → roughly **$1–2/active user/month**. Track `hint_events.source` as your
primary cost KPI from day one; if the card-hit rate drops below 70%, unit economics break.

---

## 7. Development plan

Six phases. Each has a **dogfood/exit criterion** — a thing that must be true before
moving on, not just "code written."

### Phase 0 — Foundation reset (1–2 weeks)

Rebuild the base properly. Nothing user-facing ships.

- Monorepo: `apps/api` (FastAPI), `apps/extension` (MV3 + React + Vite), `packages/shared` (types)
- Postgres + Alembic migrations for the §4 schema; Redis; Docker Compose for local dev
- Auth: email magic link or GitHub OAuth → JWT; the extension stores the token in
  `chrome.storage.session`
- CI: lint, typecheck, pytest, extension build. Port the existing 11 tests forward.
- Anthropic client wrapper: retries, structured-output helper, cost logging per call
- **Exit:** `docker compose up` gives a working API; the extension loads unpacked in
  Chrome and shows an authenticated "hello" panel on a LeetCode problem page.

### Phase 1 — The brain, for real (2–3 weeks)

Replace every hardcoded string with something that actually reasons.

- tree-sitter static analysis: Python, C++, Java, JS. Emit a `CodeSignals` struct
  (loop depth, recursion, DS used, memoization present, mutation-in-loop, early exit)
- Claude integration behind a `Mentor` interface; strict JSON schemas for every response
- **Problem card schema + generator + validator.** Build cards for the **Top 150** first,
  not all 3,500. Validator checks: hint ladder is monotonic, L1–L4 contain no code,
  complexities parse, at least 3 approaches, at least 3 pitfalls.
- Batch pipeline runner with resume-from-failure
- **Exit:** `POST /hint {slug, level, code}` returns a real, useful, code-free hint for
  any of 150 problems in any of 4 languages, and you'd be embarrassed by fewer than 1
  in 10 of them.

### Phase 2 — The extension MVP ← **dogfood point** (3 weeks)

This is where it becomes a product you personally use every day.

- `LeetCodeAdapter`: read slug from URL, language from the editor toolbar, buffer from
  the Monaco instance, verdict from the results panel (MutationObserver — LeetCode ships
  DOM changes, so write this defensively with a fallback and a "selectors broken" telemetry event)
- Side panel: Understand / Patterns / Hint / Review tabs
- **The AC gate**, enforced server-side: `session.solved_at IS NULL` → Socratic schema only
- Hint budget + escalation logging
- Stuck detector v1: idle >8min, or 3 failed submissions, or delete-retype cycling → nudge
- **Exit:** you solve 20 problems using only Alfred — no ChatGPT, no editorial — and
  the hint ladder gets you unstuck without ever handing you the answer.

### Phase 3 — Progression (2–3 weeks)

Make it something you return to tomorrow.

- Streaks with freezes, daily goal, timezone-correct rollover
- XP: clean solve > hinted solve; L4 hint costs more than L1
- Mastery model per topic (start simple: EWMA of solve quality; upgrade to Elo/BKT later)
- Hint availability tapers as mastery rises — at mastery >0.8 on a topic, L1 and L2 are
  withheld by default. This is the "reduces hints as you progress" requirement, and it's
  the part that makes the product feel like it's actually training you.
- Adaptive recommender: next problem targets the weakest topic at the edge of ability
- Spaced repetition resurfacing
- **Exit:** a 14-day streak is achievable and the recommended problems feel *right* —
  not random, not too easy, not walls.

### Phase 4 — Depth + personality (2–3 weeks)

The reason people stay after they stop needing hints.

- Post-AC suite: alternative approaches, complexity deep-dive, wrong-ways gallery,
  edge-case generator, rewrite challenges
- Meme review system: curated asset library, tag selection via Haiku, tone gating
- Roast/encourage toggle
- "Why did this work?" mode
- Extend the card KB from 150 → 800 problems (batch run)
- **Exit:** every clause of the résumé blurb is now literally true. Post-AC review is
  good enough that you read it even on problems you found easy.

### Phase 5 — Insight + interview (2–3 weeks)

- Analytics dashboard (web app, not extension): mastery over time, mistake taxonomy,
  complexity trend, hint dependence curve going *down*
- Personalized roadmap view
- Interview mode (system interrogates; no help offered)
- Contest review mode
- Card KB → full catalog
- **Exit:** the dashboard tells you something about your own weaknesses you didn't know.

### Phase 6 — Scale out

Only after Phases 0–5 have real users. Pick based on where retention actually is:

- VS Code extension (same adapter seam)
- Second judge (Codeforces or HackerRank)
- Team/instructor mode — the clearest monetization path
- System-design mentor

**Rough total to a genuinely good product: ~14–18 weeks of focused solo work.**
Phase 2 is the milestone that matters; everything before it is scaffolding and
everything after it is compounding.

---

## 8. Risks, ranked

1. **DOM fragility.** LeetCode can break your content script with any deploy. Mitigate:
   selector abstraction layer, remote-configurable selectors (ship a fix without a store
   review round-trip), loud telemetry when extraction fails, graceful degrade to
   manual paste.
2. **Unit economics.** Covered in §6. The card-hit rate is the whole ballgame. Instrument it first.
3. **Hint quality at scale.** 150 hand-checked cards will be good. 3,500 auto-generated
   ones will contain garbage. Budget for a validation pass + a user "this hint was bad"
   button feeding a review queue.
4. **Chrome Web Store review.** MV3 + broad-ish permissions + an AI feature. Expect at
   least one rejection round. Keep permissions minimal and the privacy policy explicit
   about what code leaves the browser (it does — say so plainly).
5. **Cold start / motivation.** Gamification only works with a population. A solo user
   on day 1 sees an empty dashboard. Seed with a strong onboarding path and make the
   first session deliver value with zero history.
6. **Scope.** The feature catalog has 25 entries. Phases 0–2 contain 8 of them. Resist
   the rest until the dogfood criterion in Phase 2 is met.

---

## 9. Open questions for you

- **Free vs paid?** The cost model in §6 is survivable free only with a high card-hit
  rate and a daily interaction cap. Decide before Phase 3, because it changes how
  aggressively hint budgets are tuned.
- **Chrome-only, or Firefox too?** MV3 differs; deciding late is expensive.
- **Do you want a web app at all, or is the dashboard also in the extension?** Phase 5
  assumes a web app. Extension-only is cheaper and worse.
- **Card generation ethics/quality:** are you comfortable with auto-generated hint
  ladders for the long tail, or do you want the KB capped at what you can spot-check?
