import logging
from celery import chain
from celery.result import AsyncResult
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.celery.tasks import parse_search_task, process_search_task
from app.schemas import SearchSchema
from app.extensions import limiter, redis_jobs
from app.errors import success_response, error_response
from app.audit import audit_log
from app.observability import get_request_id

bp = Blueprint("search", __name__, url_prefix="/search")
logger = logging.getLogger(__name__)
search_schema = SearchSchema()

JOB_OWNER_TTL = 3600


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
    logger.info("search input length: %s", len(search_input), extra={"request_id": request_id})

    audit_log(
        "search",
        user_id=user_id,
        outcome="success",
        details={"request_id": request_id, "input_length": len(search_input)},
    )

    result = chain(
        parse_search_task.s(search_input),
        process_search_task.s(user_id)
    ).apply_async(headers={"request_id": request_id})

    # record who owns the job so status can be checked per user
    redis_jobs.setex(f"job_owner:{result.id}", JOB_OWNER_TTL, user_id)

    return success_response(
        code="search_queued",
        message="Search request accepted and queued.",
        data={"job_id": result.id},
        status_code=202,
    )


@bp.route("/status/<job_id>", methods=["GET"])
@jwt_required()
def search_status(job_id):
    user_id = int(get_jwt_identity())
    request_id = get_request_id()

    # 404 for both missing and not-owned so job ids can't be probed
    owner = redis_jobs.get(f"job_owner:{job_id}")
    if owner is None or int(owner) != user_id:
        return error_response(
            code="job_not_found",
            message="Job not found.",
            status_code=404,
        )

    result = AsyncResult(job_id)

    if result.state == "SUCCESS":
        tabs = result.result or {}
        search_tab = tabs.get("search_results", []) if isinstance(tabs, dict) else tabs
        return success_response(
            code="search_success",
            message="Search completed successfully.",
            data={"status": "SUCCESS", "job_id": job_id, "result": search_tab},
            status_code=200,
        )

    if result.state == "FAILURE":
        logger.error(
            "search job failed: job_id=%s error=%s",
            job_id,
            result.result,
            extra={"request_id": request_id},
        )
        return error_response(
            code="search_failed",
            message="Search processing failed.",
            details={"job_id": job_id},
            status_code=500,
        )

    return success_response(
        code="search_pending",
        message="Search is currently processing.",
        data={"status": result.state, "job_id": job_id},
        status_code=200,
    )