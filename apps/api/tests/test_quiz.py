from datetime import date

import pytest

from alfred import quiz
from alfred.config import Settings


class FakeMentor:
    available = True

    def __init__(self, responses):
        self.responses = list(responses)

    def _complete_json(self, *a, **k):
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def _quiz_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_QUIZ_DIR", str(tmp_path / "quizzes"))


def _settings(vault_dir):
    return Settings(jwt_secret="x" * 32, vault_path=str(vault_dir))


def _vault(tmp_path):
    v = tmp_path / "vault"
    (v / "db").mkdir(parents=True)
    (v / "db" / "redis-persistence.md").write_text("# Redis persistence\nRDB snapshots, AOF logs every write.", encoding="utf-8")
    return v


def test_start_keeps_only_questions_grounded_in_real_notes(tmp_path):
    s = _settings(_vault(tmp_path))
    m = FakeMentor([{"questions": [
        {"question": "What does AOF log?", "answer": "every write", "source_note": "redis persistence"},
        {"question": "Invented?", "answer": "x", "source_note": "some note that does not exist"}]}])
    q = quiz.start(s, m, "redis persistence")
    assert [x.question for x in q.questions] == ["What does AOF log?"]
    assert quiz.load(q.id).topic == "redis persistence"


def test_start_without_notes_refuses(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(quiz.QuizError, match="no notes"):
        quiz.start(_settings(tmp_path / "empty"), FakeMentor([]), "kubernetes")


def test_answer_uses_model_grade_then_offline_fallback(tmp_path):
    s = _settings(_vault(tmp_path))
    m = FakeMentor([{"questions": [{"question": "q", "answer": "append only file logs every write", "source_note": "redis persistence"}]},
                    {"score": 2, "feedback": "right"}, None])
    q = quiz.start(s, m, "redis persistence")
    assert quiz.answer(m, q, 0, "logs every write").score == 2
    assert quiz.answer(m, q, 0, "append only file logs every write").feedback.startswith("graded offline")


def test_intervals_grow_on_success_and_reset_on_failure():
    assert quiz.next_interval(0, 1.0) == 2
    assert quiz.next_interval(4, 1.0) == 10
    assert quiz.next_interval(10, 0.6) == 10
    assert quiz.next_interval(10, 0.2) == 1


def test_finish_writes_due_date_and_grows_interval_next_time(tmp_path):
    v = _vault(tmp_path)
    s = _settings(v)
    m = FakeMentor([{"questions": [{"question": "q", "answer": "a", "source_note": "redis persistence"}]}, {"score": 2, "feedback": ""}])
    q = quiz.start(s, m, "redis persistence")
    quiz.answer(m, q, 0, "a")
    r1 = quiz.finish(s, q, today=date(2026, 9, 1))
    assert r1["next_due"] == "2026-09-03" and (v / "agents" / "Alfred").is_dir()
    r2 = quiz.finish(s, q, today=date.today())
    assert r2["interval_days"] == 5  # 2 * 2.5


def test_keyword_score():
    assert quiz.keyword_score("hash map constant lookup", "hash map gives constant lookup") == 2
    assert quiz.keyword_score("hash map constant lookup", "") == 0
