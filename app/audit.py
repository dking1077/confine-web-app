import logging
from flask import request


logger = logging.getLogger(__name__)


def audit_log(event, user_id=None, outcome="success", details=None):
    logger.info(
        "audit event=%s user_id=%s outcome=%s route=%s method=%s details=%s",
        event,
        user_id,
        outcome,
        request.path,
        request.method,
        details or {},
    )