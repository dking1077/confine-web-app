import threading
import time
from concurrent.futures import ThreadPoolExecutor
import pytest

PARSED = ("radiohead", "creep", "radiohead creep")


@pytest.fixture
def sf(app, monkeypatch):
    """In-memory cache + lock so the single-flight logic can be tested without redis."""
    import app.celery.tasks as tasks

    store, held, calls = {}, set(), []
    guard = threading.Lock()
    state = {"fail_first": False}

    def acquire_lock(key):
        with guard:
            if key in held:
                return None
            held.add(key)
            return key

    def wait_for_cache(key, timeout=20):
        end = time.monotonic() + 1.5
        while time.monotonic() < end:
            if key in store:
                return store[key]
            time.sleep(0.02)
        return None

    def cache_pipeline(db, user_id, artist, track, search_input):
        key = f"{artist}:{track}"
        return store.get(key), key

    def search_pipeline(db, client, user_id, artist, track, search_input, key):
        with guard:
            calls.append(1)
            first = len(calls) == 1
        time.sleep(0.3)
        if state["fail_first"] and first:
            raise RuntimeError("upstream down")
        store[key] = [{"track": track}]
        return store[key]

    monkeypatch.setattr(tasks, "acquire_lock", acquire_lock)
    monkeypatch.setattr(tasks, "release_lock", lambda lock: held.discard(lock))
    monkeypatch.setattr(tasks, "wait_for_cache", wait_for_cache)
    monkeypatch.setattr(tasks, "cache_pipeline", cache_pipeline)
    monkeypatch.setattr(tasks, "search_pipeline", search_pipeline)
    monkeypatch.setattr(tasks, "append_tabs_list", lambda uid, data, name: {name: data})
    monkeypatch.setattr(tasks, "MusixMatch", lambda api_key: object())
    app.config["MUSIXMATCH_APIKEY"] = "test"

    def run(n):
        def one(_):
            with app.app_context():
                try:
                    return tasks.process_search_task.run(PARSED, 1)
                except RuntimeError as e:
                    return e

        with ThreadPoolExecutor(n) as pool:
            return list(pool.map(one, range(n)))

    return run, calls, held, state


def test_concurrent_searches_hit_upstream_once(sf):
    run, calls, held, _ = sf
    results = run(10)

    assert len(calls) == 1
    assert all(r == {"search_results": [{"track": "creep"}]} for r in results)


def test_lock_released_after_search(sf):
    run, _, held, _ = sf
    run(3)

    assert not held


def test_followers_recover_when_leader_fails(sf):
    run, calls, held, state = sf
    state["fail_first"] = True
    results = run(3)

    errors = [r for r in results if isinstance(r, RuntimeError)]
    ok = [r for r in results if isinstance(r, dict)]
    assert len(errors) == 1
    assert len(ok) == 2
    assert not held