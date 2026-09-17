from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.tabs import append_tabs_list, fetch_lyrics, remove_tabs_list, resolve_by_id
from app.celery import analyze_items_task, process_input
from app.extensions import limiter
from app.errors import ApiError, success_response
from app.schemas import AddToPanelSchema, RemoveFromPanelSchema, AnalyzeItemsSchema, ProcessItemsSchema
import logging

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
    track_ids = data["items"]
    target_panel = data["panel"]
    user_id = int(get_jwt_identity())

    full_items = resolve_by_id(user_id, track_ids, 'search_results')
    full_items_lyrics = fetch_lyrics(full_items)

    tabs = append_tabs_list(user_id, full_items_lyrics, target_panel)
    workspace = tabs.get(target_panel, [])

    return success_response(
        code="ADD_TO_PANEL_SUCCESS",
        message="Items added to panel",
        data={"result": workspace},
        status_code=200,
    )


@bp.route("/remove_from_panel", methods=["POST"])
@limiter.limit("10/minute")
@jwt_required()
def remove_from_panel():
    data = remove_from_panel_schema.load(request.get_json())
    track_ids = data["items"]
    source_panel = data["panel"]
    user_id = int(get_jwt_identity())

    tabs = remove_tabs_list(user_id, track_ids, source_panel)
    panel_tab = tabs.get(f"{source_panel}", [])

    return success_response(
        code="REMOVE_FROM_PANEL_SUCCESS",
        message="Items removed from panel",
        data={"result": panel_tab},
        status_code=200,
    )


@bp.route("/analyze_items", methods=["POST"])
@limiter.limit("3/minute")
@jwt_required()
def analyze_items():
    data = analyze_items_schema.load(request.get_json())
    track_ids = data["items"]
    user_id = int(get_jwt_identity())

    full_items = resolve_by_id(user_id, track_ids, 'workspace')
    tracks_lyrics = [
        {
            "commontrack_id": item.get("commontrack_id", ""),
            "track_name": item.get("track_name", ""),
            "lyrics": item.get("lyrics", ""),
        }
        for item in full_items
    ]

    result = analyze_items_task.delay(tracks_lyrics)
    task_result = result.get()
    if task_result is None:
        raise ApiError("ANALYZE_FAILED", "Analyze task returned no result", 500)

    concepts_return, semantics_return = task_result

    tabs = append_tabs_list(user_id, concepts_return, 'concepts')
    concepts = tabs.get('concepts', [])
    concepts_return = [
        {
            "track": t["track"],
            "commontrack_id": t["commontrack_id"],
            "concepts": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "display_concept": c["display_concept"],
                    "evidence": c["evidence"]
                }
                for c in t["concepts"]
            ],
        }
        for t in concepts
    ]

    tabs = append_tabs_list(user_id, semantics_return, 'semantics')
    semantics = tabs.get('semantics', [])
    semantics_return = [
        {
            "track": t["track"],
            "commontrack_id": t["commontrack_id"],
            "semantics": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "display_semantic": s["display_semantic"],
                    "evidence": s["evidence"]
                }
                for s in t["semantics"]
            ],
        }
        for t in semantics
    ]

    return success_response(
        code="ANALYZE_ITEMS_SUCCESS",
        message="Items analyzed successfully",
        data={"result": {"concepts": concepts_return, "semantics": semantics_return}},
        status_code=200,
    )


@bp.route("/process_items", methods=["POST"])
@limiter.limit("3/minute")
@jwt_required()
def process_items():
    data = process_items_schema.load(request.get_json())
    user_id = int(get_jwt_identity())

    concept_ids = data["concept_ids"]
    semantic_ids = data["semantic_ids"]
    instructions = data["instructions"]
    input_text = data["input_text"]

    concepts = resolve_by_id(user_id, concept_ids, 'concepts')
    semantics = resolve_by_id(user_id, semantic_ids, 'semantics')

    display_result = process_input.delay(concepts, semantics, instructions, input_text)
    text_result = display_result.get()

    logger.info("display result:\n %s", text_result)

    return success_response(
        code="PROCESS_ITEMS_SUCCESS",
        message="Items processed successfully",
        data={"result": {"display_result": text_result}},
        status_code=200,
    )