from celery import signals
import json
import logging
from app import extensions

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


@signals.task_success.connect
def task_success(sender=None, result=None, task=None, **kwargs):
    request_id = get_request_id(task)
    logger.info("[%s] SUCCESS request_id=%s", task_name(sender), request_id)


@signals.task_failure.connect
def task_failed(sender=None, exception=None, task=None, task_id=None, **kwargs):
    request_id = get_request_id(task)
    logger.error(
        "[%s] FAILED error=%s request_id=%s", task_name(sender), exception, request_id
    )

    entry = {"task": task_name(sender), "task_id": task_id, "error": str(exception), "request_id": request_id}
    extensions.redis_jobs.lpush(DEAD_LETTER_KEY, json.dumps(entry))
    extensions.redis_jobs.ltrim(DEAD_LETTER_KEY, 0, DEAD_LETTER_MAX - 1)


@signals.task_retry.connect
def task_retried(sender=None, reason=None, task=None, **kwargs):
    request_id = get_request_id(task)
    logger.warning(
        "[%s] RETRY reason=%s request_id=%s", task_name(sender), reason, request_id
    )