import logging
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from celery.result import AsyncResult
from app.tabs import append_tabs_list, fetch_lyrics, remove_tabs_list, resolve_by_id
from app.celery import analyze_items_task, process_input
from app.extensions import limiter
from app.schemas import AddToPanelSchema, RemoveFromPanelSchema, AnalyzeItemsSchema, ProcessItemsSchema
from app.errors import success_response, error_response
from app.audit import audit_log

logger = logging.getLogger(__name__)
bp = Blueprint("tabs", __name__, url_prefix="/tabs")

add_to_panel_schema = AddToPanelSchema()
remove_from_panel_schema = RemoveFromPanelSchema()
analyze_items_schema = AnalyzeItemsSchema()
process_items_schema = ProcessItemsSchema()


@bp.route("/add_to_panel", methods=["POST"])
@limiter.limit("5/minute")
@jwt_required()
def add_to_panel():
    data = add_to_panel_schema.load(request.get_json())
    track_ids = data.get("items", [])
    target_panel = data["panel"]
    user_id = int(get_jwt_identity())

    full_items = resolve_by_id(user_id, track_ids, "search_results")
    full_items_lyrics = fetch_lyrics(full_items)

    tabs = append_tabs_list(user_id, full_items_lyrics, target_panel)
    workspace = tabs.get(target_panel, [])

    audit_log(
        "add_to_panel",
        user_id=user_id,
        outcome="success",
        details={"panel": target_panel, "items_count": len(track_ids)},
    )

    return success_response(
        code="ADD_TO_PANEL_SUCCESS",
        message="Items added to panel successfully.",
        data={"result": workspace},
        status_code=200,
    )


@bp.route("/remove_from_panel", methods=["POST"])
@limiter.limit("10/minute")
@jwt_required()
def remove_from_panel():
    data = remove_from_panel_schema.load(request.get_json())
    track_ids = data.get("items", [])
    source_panel = data["panel"]
    user_id = int(get_jwt_identity())

    tabs = remove_tabs_list(user_id, track_ids, source_panel)
    panel_tab = tabs.get(f"{source_panel}", [])

    audit_log(
        "remove_from_panel",
        user_id=user_id,
        outcome="success",
        details={"panel": source_panel, "items_count": len(track_ids)},
    )

    return success_response(
        code="REMOVE_FROM_PANEL_SUCCESS",
        message="Items removed from panel successfully.",
        data={"result": panel_tab},
        status_code=200,
    )


@bp.route("/analyze_items", methods=["POST"])
@limiter.limit("3/minute")
@jwt_required()
def analyze_items():
    data = analyze_items_schema.load(request.get_json())
    track_ids = data.get("items", [])
    user_id = int(get_jwt_identity())

    full_items = resolve_by_id(user_id, track_ids, "workspace")
    tracks_lyrics = [
        {
            "commontrack_id": item.get("commontrack_id", ""),
            "track_name": item.get("track_name", ""),
            "lyrics": item.get("lyrics", ""),
        }
        for item in full_items
    ]

    result = analyze_items_task.delay(user_id, tracks_lyrics)

    audit_log(
        "analyze_items",
        user_id=user_id,
        outcome="success",
        details={"items_count": len(track_ids)},
    )

    return success_response(
        code="ANALYZE_ITEMS_QUEUED",
        message="Analysis request accepted and queued.",
        data={"job_id": result.id},
        status_code=202,
    )


@bp.route("/process_items", methods=["POST"])
@limiter.limit("3/minute")
@jwt_required()
def process_items():
    data = process_items_schema.load(request.get_json())
    user_id = int(get_jwt_identity())

    concept_ids = data.get("concept_ids", [])
    semantic_ids = data.get("semantic_ids", [])
    instructions = data.get("instructions", "")
    input_text = data.get("input_text", "")

    concepts = resolve_by_id(user_id, concept_ids, "concepts")
    semantics = resolve_by_id(user_id, semantic_ids, "semantics")

    display_result = process_input.delay(concepts, semantics, instructions, input_text)

    audit_log(
        "process_items",
        user_id=user_id,
        outcome="success",
        details={
            "concept_ids_count": len(concept_ids),
            "semantic_ids_count": len(semantic_ids),
        },
    )

    return success_response(
        code="PROCESS_ITEMS_QUEUED",
        message="Processing request accepted and queued.",
        data={"job_id": display_result.id},
        status_code=202,
    )


@bp.route("/status/<job_id>", methods=["GET"])
@jwt_required()
def tab_status(job_id):
    result = AsyncResult(job_id)

    if result.state == "SUCCESS":
        return success_response(
            code="TAB_TASK_SUCCESS",
            message="Task completed successfully.",
            data={"status": "SUCCESS", "job_id": job_id, "result": result.result},
            status_code=200,
        )

    if result.state == "FAILURE":
        return error_response(
            code="TAB_TASK_FAILED",
            message="Task processing failed.",
            details={
                "job_id": job_id,
                "error": str(result.result),
                "traceback": str(result.traceback) if result.traceback else None,
            },
            status_code=500,
        )

    return success_response(
        code="TAB_TASK_PENDING",
        message="Task is currently processing.",
        data={"status": result.state, "job_id": job_id},
        status_code=200,
    )