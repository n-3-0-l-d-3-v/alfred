# LeetLearn

A Duolingo-for-LeetCode coding mentor. It makes you solve the problem yourself
with a Socratic hint ladder, then — *only after you pass* — opens the full
teaching surface: every approach, every wrong turn, complexity deep-dives, and
memed code review. Free, with hard daily caps to keep it that way.

The defensible idea is the **AC gate**: before a passing submission the mentor is
structurally incapable of emitting solution code; after, everything unlocks.
That's what separates it from "a slower ChatGPT." See [PLAN.md](PLAN.md) for the
full architecture, cost model, and phased roadmap.

## Status

| Phase | | |
|---|---|---|
| 0 — Foundation | 🟢 done | API, GitHub OAuth → JWT, Alembic migrations, Postgres, Docker, Fly config, CI-ready tests. |
| 1 — The brain | 🟡 in progress | 5-language parsing, AC gate, personas, memes, failure gallery, offline review all done. **The card KB is still only 2 problems** — the archetype engine and NeetCode 150 are the active work. |
| 2 — Extension MVP | 🟡 built, needs live validation | Chrome + Firefox builds load; DOM selectors need checking against real LeetCode. |

**89 tests green** — 75 Python + 14 JavaScript.

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
- **Five review personas** — Mentor, Roast, Interviewer, Pragmatist, Professor.
  Voice changes; findings are identical, so a fun persona is never worse information.
- **Tone-gated memes** — curated library, and a roast automatically softens to
  gentle after a struggle (3+ hints or 3+ failed attempts).
- **Cross-browser extension** — one source, Chrome + Firefox builds, assembled by
  a Python script so there's no Node/npm build toolchain.

## Repo layout

```
PLAN.md            architecture, cost model, 6-phase roadmap, risks
apps/
  api/             FastAPI backend  — built, runnable, 53 tests
  extension/       Chrome + Firefox MV3 — built, 14 tests
```

## The cost fence (why it can be free)

- Hints are served from **pre-generated Problem Cards** (a DB read), not live LLM
  calls. Target ≥80% card-hit rate.
- **Daily caps** in `apps/api/leetlearn/config.py` bound worst-case spend per user:
  40 free card hints/day, 25 paid LLM calls/day (~$0.15/day worst case at Haiku rates).
- Card generation for the whole catalog is a **one-time ~$166 Batch job**, not a
  per-request cost.

Track `hint_events.source` (`card` vs `llm`) — it's the KPI that governs unit economics.
