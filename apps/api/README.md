# LeetLearn API

FastAPI backend. Runs fully **without an API key** — hints are served from
pre-generated Problem Cards (a DB/file read), and code review falls back to a
static-analysis heuristic. An Anthropic key only enriches the personalized paths.

## Run it

The extension does nothing without this running, so there is one command that
sets up whatever is missing — virtualenv, dependencies, and a `.env` with a
freshly generated JWT secret — and then starts the server:

```powershell
powershell -ExecutionPolicy Bypass -File apps\api\run.ps1
```

Leave that window open while you use the extension. On macOS/Linux, or if you
prefer the steps spelled out:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate         # .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn leetlearn.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API.

## Try the flow

```bash
# 1. dev login -> token
curl -X POST localhost:8000/auth/dev-login -H "content-type: application/json" -d "{\"email\":\"you@test.dev\"}"
# 2. start a session (any slug works - unauthored problems get a generated card)
curl -X POST localhost:8000/sessions -H "Authorization: Bearer llt_1" -H "content-type: application/json" -d "{\"slug\":\"two-sum\"}"
# 3. ask for hints L1..L4 (code-free, free). L5 is blocked until you pass.
curl -X POST localhost:8000/sessions/1/hint -H "Authorization: Bearer llt_1" -H "content-type: application/json" -d "{\"level\":1}"
# 4. mark it solved -> unlocks approaches, review, XP, streak
curl -X POST localhost:8000/sessions/1/verdict -H "Authorization: Bearer llt_1" -H "content-type: application/json" -d "{\"verdict\":\"Accepted\"}"
```

## Test

```bash
pip install -r requirements.txt
pytest -q
```

`tests/test_ac_gate.py` is the load-bearing suite: it proves no solution code
can reach a learner before a passing submission, through any path.

## Layout

```
leetlearn/
  config.py          settings + the daily cap limits (the cost fence)
  models.py          SQLAlchemy schema (users, sessions, hint_events, streaks, xp)
  db.py              engine + session factory
  analysis/          static analysis -> CodeSignals (python via ast; tree-sitter later)
  mentor/
    contracts.py     PreACHint (code-free) + looks_like_code guard  <- the AC gate, schema layer
    cards.py         Problem Card model + loader (validates ladders code-free)
    llm.py           Claude wrapper, degrades to offline with no key
    service.py       HintService: AC-gate serving + offline review  <- the AC gate, serving layer
  gamification/
    budget.py        daily caps (card vs llm)
    streaks.py       streak + freezes
    progress.py      on_verdict: flip gate, award XP, advance streak
  cards_data/        seed Problem Cards (JSON)
```

## What's a dev stub (replace before real users)

- **Auth** — token is literally `llt_<user_id>`. Swap for magic-link / OAuth → JWT.
- **DB** — SQLite; models are Postgres-portable. Add Alembic migrations.
- **Cards** — JSON files plus archetype specializations, loaded into memory;
  production uses the `problem_cards` table. Problems with no authored card get
  one generated at request time from the archetype their tags and statement
  infer to (`mentor/infer.py`, `mentor/synth.py`), marked `verified: false`.
- **tree-sitter** — only Python static analysis is wired; other languages return an
  honest "not yet" and still get card-based hints.
