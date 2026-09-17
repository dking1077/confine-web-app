from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Blueprint, request
from app.celery.tasks import process_search_task, parse_search_task
from app.schemas import SearchSchema
from app.extensions import limiter
from app.errors import ApiError, success_response
from celery import chain
import logging
import uuid

bp = Blueprint("search", __name__, url_prefix="/search")
logger = logging.getLogger(__name__)
search_schema = SearchSchema()


# search route
@bp.route("/", methods=["POST"])
@limiter.limit("10/minute")
@jwt_required()
def search():
    data = search_schema.load(request.get_json())
    request_id = str(uuid.uuid4())

    user_id = int(get_jwt_identity())
    search_input = data["search_input"]

    logger.info('\n===== PROCESS STARTED =====')
    logger.info('user_id: %s', user_id)
    logger.info("raw html input: %s", search_input)

    result = chain(
        parse_search_task.s(search_input),
        process_search_task.s(user_id)
    ).apply_async(headers={"request_id": request_id})

    tabs = result.get()
    if tabs is None:
        raise ApiError("SEARCH_FAILED", "Search returned no result", 500)

    search_tab = tabs.get("search_results", [])

    return success_response(
        code="SEARCH_SUCCESS",
        message="Search completed successfully",
        data={
            "job_id": result.id,
            "result": search_tab,
        },
        status_code=200,
    )