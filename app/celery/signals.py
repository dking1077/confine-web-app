import time
import json
import logging
from celery import signals
from app import extensions
from app.metrics import celery_task_total, celery_task_duration_seconds

logger = logging.getLogger(__name__)

DEAD_LETTER_KEY = "dead_letter"
DEAD_LETTER_MAX = 100


def task_name(sender):
    return sender.name.split(".")[-1]


def get_request_id(task):
    if not task:
        return None
    request = getattr(task, "request", None)
    if not request:
        return None
    headers = getattr(request, "headers", None)
    if not headers:
        return None
    return headers.get("request_id")


@signals.worker_ready.connect
def celery_started(**kwargs):
    logger.info("===== CELERY STARTED =====")


@signals.task_prerun.connect
def task_started(sender=None, task=None, **kwargs):
    request_id = get_request_id(task)
    logger.info("\n[%s] START request_id=%s", task_name(sender), request_id)
    # Store start time on the task request
    if task and hasattr(task, "request"):
        task.request._start_time = time.perf_counter()


@signals.task_success.connect
def task_success(sender=None, result=None, task=None, **kwargs):
    name = task_name(sender)
    request_id = get_request_id(task)

    # Duration
    if task and hasattr(task, "request") and hasattr(task.request, "_start_time"):
        duration = time.perf_counter() - task.request._start_time
        celery_task_duration_seconds.labels(task=name).observe(duration)

    celery_task_total.labels(task=name, status="success").inc()
    logger.info("[%s] SUCCESS request_id=%s", name, request_id)


@signals.task_failure.connect
def task_failed(sender=None, exception=None, task=None, task_id=None, **kwargs):
    name = task_name(sender)
    request_id = get_request_id(task)

    if task and hasattr(task, "request") and hasattr(task.request, "_start_time"):
        duration = time.perf_counter() - task.request._start_time
        celery_task_duration_seconds.labels(task=name).observe(duration)

    celery_task_total.labels(task=name, status="failure").inc()

    logger.error("[%s] FAILED error=%s request_id=%s", name, exception, request_id)

    entry = {
        "task": name,
        "task_id": task_id,
        "error": str(exception),
        "request_id": request_id,
    }
    extensions.redis_jobs.lpush(DEAD_LETTER_KEY, json.dumps(entry))
    extensions.redis_jobs.ltrim(DEAD_LETTER_KEY, 0, DEAD_LETTER_MAX - 1)


@signals.task_retry.connect
def task_retried(sender=None, reason=None, task=None, **kwargs):
    name = task_name(sender)
    request_id = get_request_id(task)

    celery_task_total.labels(task=name, status="retry").inc()
    logger.warning("[%s] RETRY reason=%s request_id=%s", name, reason, request_id)