"""Quiz yourself on your OWN notes, graded locally, scheduled for spaced review.

  start(topic)   -> questions generated only from the vault notes on that topic
  answer(i, txt) -> graded against the reference answer from those notes
  finish()       -> writes agents/Alfred/quiz-<topic>.md with mastery + next_due

Spacing is SM-2-lite: a well-answered topic's interval grows (x2.5), a weak one
resets to 1 day. `next_due` in that note is what Jarvis's daily briefing and the
Obsidian dashboard read. No network: model calls go to the local backend.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from . import vault
from .config import Settings
from .mentor.llm import Mentor

_Q_SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {"type": "object", "properties": {
        "question": {"type": "string"}, "answer": {"type": "string"}, "source_note": {"type": "string"}},
        "required": ["question", "answer", "source_note"]}}},
    "required": ["questions"],
}
_GRADE_SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "integer", "minimum": 0, "maximum": 2}, "feedback": {"type": "string"}},
    "required": ["score", "feedback"],
}


class QuizError(Exception):
    pass


@dataclass
class Question:
    question: str
    answer: str
    source_note: str
    score: Optional[int] = None
    feedback: str = ""


@dataclass
class Quiz:
    id: str
    topic: str
    questions: list[Question] = field(default_factory=list)


def _store_dir() -> Path:
    d = Path(os.environ.get("ALFRED_QUIZ_DIR") or Path.home() / ".alfred" / "quizzes")
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(q: Quiz) -> None:
    (_store_dir() / f"{q.id}.json").write_text(json.dumps(asdict(q)), encoding="utf-8")


def load(quiz_id: str) -> Quiz:
    if not re.fullmatch(r"[a-f0-9]{12}", quiz_id or ""):
        raise QuizError("invalid quiz id")
    p = _store_dir() / f"{quiz_id}.json"
    if not p.exists():
        raise QuizError(f"no quiz {quiz_id}")
    d = json.loads(p.read_text(encoding="utf-8"))
    return Quiz(d["id"], d["topic"], [Question(**x) for x in d["questions"]])


def start(settings: Settings, mentor: Mentor, topic: str, n: int = 3) -> Quiz:
    notes = vault.find_relevant_notes(settings, topic, limit=4)
    if not notes:
        raise QuizError(f"no notes on {topic!r} in your vault yet; capture some first (friday note ...)")
    if not mentor.available:
        raise QuizError("no local model available (start Ollama)")
    context = vault.notes_as_context(notes, max_chars=4000)
    system = ("You write short-answer quiz questions for a CS student, using ONLY facts stated in their notes. "
              "Each answer must be checkable from the notes. Name the note title each question came from.")
    user = f"Topic: {topic}\nWrite {n} questions.\n\nNOTES (titles as headings):\n{context}"
    data = mentor._complete_json(system, user, _Q_SCHEMA, max_tokens=900) or {}
    titles = {x.title for x in notes}
    qs = []
    for item in data.get("questions", [])[:n]:
        src = str(item.get("source_note", "")).strip().strip("#").strip().lower()
        match = next((t for t in titles if src and (src in t or t in src)), None)
        if match and item.get("question") and item.get("answer"):  # ungrounded questions are dropped
            qs.append(Question(item["question"].strip(), item["answer"].strip(), match))
    if not qs:
        raise QuizError("the model produced no questions grounded in your notes; try a more specific topic")
    quiz = Quiz(secrets.token_hex(6), topic, qs)
    save(quiz)
    return quiz


def keyword_score(reference: str, answer: str) -> int:
    """Offline fallback grader: share of reference keywords present (0/1/2)."""
    ref = {w for w in re.findall(r"[a-z0-9]{4,}", reference.lower())}
    if not ref:
        return 0
    hit = len(ref & set(re.findall(r"[a-z0-9]{4,}", answer.lower()))) / len(ref)
    return 2 if hit >= 0.6 else 1 if hit >= 0.25 else 0


def answer(mentor: Mentor, quiz: Quiz, index: int, text: str) -> Question:
    if not 0 <= index < len(quiz.questions):
        raise QuizError(f"question index must be 0..{len(quiz.questions) - 1}")
    q = quiz.questions[index]
    data = None
    if mentor.available and text.strip():
        data = mentor._complete_json(
            "Grade a student's short answer against the reference. 2 = correct and complete, "
            "1 = partly right, 0 = wrong or empty. Judge correctness only: extra correct detail or wording "
            "different from the reference is NOT a mistake. Feedback in one or two sentences.",
            f"Question: {q.question}\nReference answer: {q.answer}\nStudent answer: {text}",
            _GRADE_SCHEMA, max_tokens=200)
    if data and data.get("score") in (0, 1, 2):
        q.score, q.feedback = int(data["score"]), str(data.get("feedback", "")).strip()
    else:
        q.score = keyword_score(q.answer, text)
        q.feedback = "graded offline by keyword overlap"
    save(quiz)
    return q


def next_interval(prev_days: int, ratio: float) -> int:
    if ratio >= 0.8:
        return max(2, round(max(prev_days, 1) * 2.5))
    if ratio >= 0.5:
        return max(1, prev_days)
    return 1


def finish(settings: Settings, quiz: Quiz, today: Optional[date] = None) -> dict:
    graded = [q.score for q in quiz.questions if q.score is not None]
    if not graded:
        raise QuizError("answer at least one question first")
    today = today or date.today()
    ratio = sum(graded) / (2 * len(graded))
    prev = _previous_interval(settings, quiz.topic)
    days = next_interval(prev, ratio)
    due = today + timedelta(days=days)
    path = vault.write_progress_note(settings, user_handle="me", archetype=f"quiz {quiz.topic}",
                                     streak_days=0, mastery=ratio, next_due=due,
                                     extra={"interval_days": days, "kind": "quiz"})
    return {"mastery": round(ratio, 2), "next_due": due.isoformat(), "interval_days": days,
            "note": str(path) if path else None}


def _previous_interval(settings: Settings, topic: str) -> int:
    root = vault._vault_root(settings)
    if root is None:
        return 0
    slug = re.sub(r"[^a-z0-9]+", "-", f"me-quiz {topic}".lower()).strip("-")
    p = root / vault.WRITE_SUBDIR / f"{slug}.md"
    if not p.exists():
        return 0
    m = re.search(r"^interval_days: (\d+)", p.read_text(encoding="utf-8"), re.MULTILINE)
    return int(m.group(1)) if m else 0
