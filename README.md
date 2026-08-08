# LeetLearn

A Duolingo-for-LeetCode coding mentor. It makes you solve the problem yourself
with a Socratic hint ladder, then — *only after you pass* — opens the full
teaching surface: every approach, every wrong turn, complexity deep-dives, and
and a code review that reads what you actually wrote. Free, and it runs
with no API key at all.

The defensible idea is the **AC gate**: before a passing submission the mentor is
structurally incapable of emitting solution code; after, everything unlocks.
That's what separates it from "a slower ChatGPT." See [PLAN.md](PLAN.md) for the
full architecture, cost model, and phased roadmap.

## Status

| Phase | | |
|---|---|---|
| 0 — Foundation | 🟢 done | API, GitHub OAuth → JWT, Alembic migrations, Postgres, Docker, Fly config, CI-ready tests. |
| 1 — The brain | 🟢 mostly done | 5-language parsing, AC gate, six personas, reactions, failure gallery, code-aware hints and review. 29 pattern archetypes; **31 cards and growing** toward the NeetCode 150. |
| 2 — Extension MVP | 🟢 validated on live LeetCode | Reads the editor through Monaco, not DOM scraping. Interview mode and the post-AC gallery are wired. |
| 3 — Progression | 🔴 not started | Mastery model, hint tapering, spaced repetition, adaptive recommender. |

**351 tests green** — 323 Python + 28 JavaScript.

**What works end to end today** (no API key needed): sign in → open a LeetCode
problem → Socratic hint ladder L1–L4 → the AC gate blocks the full solution →
pass a submission → approaches, a five-persona code review, complexity
breakdown, a concrete "what would have gone wrong" gallery, memes, XP and streaks.

```bash
cd apps/api && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

Set two env vars (a `.env` in `apps/api/` works) — the server fails closed
without them, by design:

```bash
LEETLEARN_JWT_SECRET=<python -c "import secrets; print(secrets.token_urlsafe(32))">
LEETLEARN_DEV_AUTH_ENABLED=true
```

```bash
cd apps/api && pytest -q && alembic upgrade head && uvicorn leetlearn.main:app --reload
```

```bash
cd apps/extension && python build.py
```

For GitHub sign-in, register an OAuth app whose callback is the value of
`chrome.identity.getRedirectURL()` and set `LEETLEARN_GITHUB_CLIENT_ID` /
`LEETLEARN_GITHUB_CLIENT_SECRET`. Postgres locally: `docker compose up`.

Then load `apps/extension/dist/chrome` (or `dist/firefox`) — see
[apps/extension/README.md](apps/extension/README.md).

## What's built

- **Static analysis in 5 languages** — Python (stdlib `ast`), plus C++, Java,
  JavaScript/TypeScript and Go via tree-sitter. Detects loop nesting, recursion,
  memoization, data structures, and estimates complexity.
- **The AC gate**, enforced in two independent layers, with tests that prove no
  solution code can reach a learner pre-AC through any path.
- **Reviews that teach, not just fault-find** — four lenses (correctness,
  complexity, robustness, alternatives), always-present "what you did well", a
  **failure gallery** showing the exact input that breaks each common mistake and
  the wrong output it produces, plus rewrite challenges.
- **Code-aware hints** — every nudge opens with an observation about what you
  actually wrote, and rungs you've already passed are skipped. Broken code gets
  the parser's complaint instead of a Socratic question about hash maps.
- **Interview mode** — questions generated from your submission (a hash map gets
  asked about collisions; unmemoised recursion gets asked how big the call tree
  is), with model answers withheld until you commit to your own.
- **Six personas** — Mentor, Deadpan, Roast, Interviewer, Pragmatist, Professor.
  Each reorders and retitles the whole review, not just the headline; findings
  are identical, so a fun persona is never worse information. Reaction stamps
  are tone-gated and soften automatically after a struggle.
- **A platform seam** — LeetCode today, and a generic paste-anywhere adapter so
  the teaching works on any site or assignment.
- **Cross-browser extension** — one source, Chrome + Firefox builds, assembled by
  a Python script so there's no Node/npm build toolchain.

## Repo layout

```
PLAN.md            architecture, cost model, 6-phase roadmap, risks
apps/
  api/             FastAPI backend — 323 tests
  extension/       Chrome + Firefox MV3 — 28 tests
```

## The cost fence (why it can be free)

- **Nothing costs anything.** Hints come from Problem Cards (a DB read),
  personalization comes from static analysis, and reviews are computed offline.
  With no `ANTHROPIC_API_KEY` set, every feature above still works.
- Cards are **built from 29 pattern archetypes**, not generated per problem.
  PLAN.md budgeted a one-time ~$166 batch job for the catalog; the archetype
  engine replaced it, because the teaching content for a problem is mostly a
  property of its pattern rather than the problem.
- **Daily caps** in `apps/api/leetlearn/config.py` bound the worst case if the
  optional LLM path is ever switched on: 40 card hints/day, 25 model calls/day.

Track `hint_events.source` (`card` vs `llm`) — it's the KPI that governs unit economics.
