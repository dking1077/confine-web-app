import json
import pytest
from app.extensions import celery
import app.celery.tasks as tasks
from app.celery import signals  # noqa: F401  (registers handlers)


@pytest.fixture(autouse=True)
def eager(app):
    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = False
    yield
    celery.conf.task_always_eager = False


def test_task_retries_then_succeeds(app, monkeypatch):
    calls = []

    class FlakyAI:
        def __init__(self, **kw):
            pass

        def parse_search(self, text):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("timeout")
            return "radiohead", "creep"

    monkeypatch.setattr(tasks, "AIService", FlakyAI)
    app.config.update(OPENROUTER_APIKEY="k", OPENROUTER_MODEL="m")

    with app.app_context():
        res = tasks.parse_search_task.apply(args=("radiohead creep",))

    assert res.successful()
    assert len(calls) == 3


def test_exhausted_retries_go_to_dead_letter(app, monkeypatch):
    import app.extensions as ext

    class BrokenAI:
        def __init__(self, **kw):
            pass

        def parse_search(self, text):
            raise RuntimeError("upstream down")

    monkeypatch.setattr(tasks, "AIService", BrokenAI)
    app.config.update(OPENROUTER_APIKEY="k", OPENROUTER_MODEL="m")

    with app.app_context():
        res = tasks.parse_search_task.apply(args=("radiohead creep",))

    assert res.failed()
    entries = [json.loads(e) for e in ext.redis_jobs.lrange("dead_letter", 0, -1)]
    assert len(entries) == 1
    assert entries[0]["task"] == "parse_search_task"
    assert "upstream down" in entries[0]["error"]