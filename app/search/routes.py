import logging
from celery import chain
from celery.result import AsyncResult
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.celery.tasks import parse_search_task, process_search_task
from app.schemas import SearchSchema
from app.extensions import limiter
from app.errors import success_response, error_response
from app.audit import audit_log
from app.observability import get_request_id

bp = Blueprint("search", __name__, url_prefix="/search")
logger = logging.getLogger(__name__)
search_schema = SearchSchema()


@bp.route("/", methods=["POST"])
@limiter.limit("10/minute")
@jwt_required()
def search():
    data = search_schema.load(request.get_json())
    user_id = int(get_jwt_identity())
    search_input = data["search_input"]
    request_id = get_request_id()

    logger.info("\n===== PROCESS STARTED =====", extra={"request_id": request_id})
    logger.info("user_id: %s", user_id, extra={"request_id": request_id})
    logger.info("raw html input: %s", search_input, extra={"request_id": request_id})

    audit_log(
        "search",
        user_id=user_id,
        outcome="success",
        details={"request_id": request_id, "search_input": search_input},
    )

    result = chain(
        parse_search_task.s(search_input),
        process_search_task.s(user_id)
    ).apply_async(headers={"request_id": request_id})

    return success_response(
        code="SEARCH_QUEUED",
        message="Search request accepted and queued.",
        data={"job_id": result.id},
        status_code=202,
    )


@bp.route("/status/<job_id>", methods=["GET"])
@jwt_required()
def search_status(job_id):
    result = AsyncResult(job_id)

    if result.state == "SUCCESS":
        tabs = result.result or {}
        search_tab = tabs.get("search_results", []) if isinstance(tabs, dict) else tabs
        return success_response(
            code="SEARCH_SUCCESS",
            message="Search completed successfully.",
            data={"status": "SUCCESS", "job_id": job_id, "result": search_tab},
            status_code=200,
        )

    if result.state == "FAILURE":
        return error_response(
            code="SEARCH_FAILED",
            message="Search processing failed.",
            details={
                "job_id": job_id,
                "error": str(result.result),
                "traceback": str(result.traceback) if result.traceback else None,
            },
            status_code=500,
        )

    return success_response(
        code="SEARCH_PENDING",
        message="Search is currently processing.",
        data={"status": result.state, "job_id": job_id},
        status_code=200,
    )