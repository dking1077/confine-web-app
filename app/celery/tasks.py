import logging
from flask import current_app
from app import extensions
from app.extensions import celery
from app.logic import cache_pipeline, search_pipeline
from app.services import AIService, MusixMatch
from app.tabs import append_tabs_list, stable_id
from app.schemas import validate_concepts, validate_semantics


logger = logging.getLogger(__name__)


def task_request_id(task):
    request = getattr(task, "request", None)
    if not request:
        return "-"
    headers = getattr(request, "headers", None) or {}
    return headers.get("request_id", "-")


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def parse_search_task(self, search_input):
    request_id = task_request_id(self)
    try:
        ai_client = AIService(api_key=current_app.config["OPENROUTER_APIKEY"], model=current_app.config["OPENROUTER_MODEL"])
        artist_input, track_input = ai_client.parse_search(search_input)

        logger.info(
            "parsed raw input: artist=%s, track=%s",
            artist_input,
            track_input,
            extra={"request_id": request_id},
        )
        return artist_input, track_input, search_input

    except Exception as e:
        logger.warning("parse_search_task failed: %s", e, extra={"request_id": request_id})
        raise e


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_search_task(self, parsed_data, user_id):
    request_id = task_request_id(self)
    artist_input, track_input, search_input = parsed_data
    try:
        cached_data, cache_key = cache_pipeline(extensions.db_session, user_id, artist_input, track_input, search_input)
        if cached_data:
            tabs = append_tabs_list(user_id, cached_data, "search_results")
            return tabs

        api_client = MusixMatch(api_key=current_app.config["MUSIXMATCH_APIKEY"])
        search_result = search_pipeline(extensions.db_session, api_client, user_id, artist_input, track_input, search_input, cache_key)

        tabs = append_tabs_list(user_id, search_result, "search_results")

        extensions.db_session.commit()
        return tabs

    except Exception as e:
        extensions.db_session.rollback()
        logger.warning("process_search_task failed: %s", e, extra={"request_id": request_id})
        raise e

    finally:
        extensions.db_session.remove()


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def analyze_items_task(self, tracks_lyrics):
    request_id = task_request_id(self)
    try:
        logger.info("analyzing items lyrics=%s", len(tracks_lyrics), extra={"request_id": request_id})
        ai_client = AIService(api_key=current_app.config["OPENROUTER_APIKEY"], model=current_app.config["OPENROUTER_MODEL"])

        concepts = validate_concepts(ai_client, tracks_lyrics) or []
        for t in concepts:
            for c in t.get("concepts", []):
                c["id"] = stable_id(
                    "c",
                    t["commontrack_id"],
                    c.get("name", ""),
                    c.get("evidence", "")
                )
        logger.info("concepts fetched=%s", len(concepts), extra={"request_id": request_id})

        semantics = validate_semantics(ai_client, tracks_lyrics) or []
        for t in semantics:
            for s in t.get("semantics", []):
                s["id"] = stable_id(
                    "s",
                    t["commontrack_id"],
                    s.get("name", ""),
                    s.get("evidence", "")
                )
        logger.info("semantics fetched=%s", len(semantics), extra={"request_id": request_id})

        return concepts, semantics

    except Exception as e:
        logger.warning("analyze_items_task failed: %s", e, extra={"request_id": request_id})
        raise e


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_input(self, concepts, semantics, instructions, input_text):
    request_id = task_request_id(self)
    try:
        applied = len(concepts) + len(semantics)
        logger.info("applying transforms=%s", applied, extra={"request_id": request_id})

        ai_client = AIService(api_key=current_app.config["OPENROUTER_APIKEY"], model=current_app.config["OPENROUTER_MODEL"])
        display_result = ai_client.transform_lyrics(concepts, semantics, instructions, input_text)

        return display_result

    except Exception as e:
        logger.warning("process_input failed: %s", e, extra={"request_id": request_id})
        raise e