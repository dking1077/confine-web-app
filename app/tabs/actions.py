from app.cache import tab_key, tab_cache_set
from app.logic import get_tab_cache
from app.services import MusixMatch
from flask import current_app
import logging
import hashlib

logger = logging.getLogger(__name__)


def append_tabs_list(user_id, items_list, tabs_listname):
    """
    adds the items to the tabs cache - for specific panel
    """
    tabs = get_tab_cache(user_id)
    existing_ids = {
        item["commontrack_id"]
        for item in tabs[tabs_listname]
    }
    for item in items_list:
        track_id = item["commontrack_id"]
        if track_id not in existing_ids:
            tabs[tabs_listname].append(item)
            existing_ids.add(track_id)
    key = tab_key(user_id, tabs["tabs_id"])
    tab_cache_set(key, tabs)
    logger.info("items list appended to tabs list:%s=%s", tabs_listname, len(tabs[tabs_listname]))
    return tabs


def resolve_by_id(user_id, track_ids, panel):
    tabs = get_tab_cache(user_id)
    tabs_panel = tabs.get(panel, [])
    if panel in ["concepts", "semantics"]:
        track_ids = [str(track_id) for track_id in track_ids]
        lookup = {}
        for track_item in tabs_panel:
            for nested_item in track_item.get(panel, []):
                item_id = nested_item.get("id")
                if item_id is not None:
                    lookup[str(item_id)] = nested_item
    else:
        track_ids = [int(track_id) for track_id in track_ids]
        lookup = {
            int(item["commontrack_id"]): item
            for item in tabs_panel
            if item.get("commontrack_id") is not None
        }
    resolved = [
        lookup[track_id]
        for track_id in track_ids
        if track_id in lookup
    ]
    logger.info("track_ids resolved: %s", len(resolved))
    return resolved


def fetch_lyrics(full_items):
    full_items_lyrics = []
    api_client = MusixMatch(api_key=current_app.config["MUSIXMATCH_APIKEY"])
    for item in full_items:
        track_id = item["commontrack_id"]
        lyrics = api_client.get_lyrics(track_id)
        item["lyrics"] = lyrics
        full_items_lyrics.append(item)
    return full_items_lyrics


def remove_tabs_list(user_id, track_ids, tabs_listname):
    tabs = get_tab_cache(user_id)
    remove_ids = {str(track_id) for track_id in track_ids}
    if tabs_listname in ("concepts", "semantics"):
        groups = tabs.get(tabs_listname, [])
        for group in groups:
            items = group.get(tabs_listname, [])
            group[tabs_listname] = [
                item for item in items
                if str(item.get("id")) not in remove_ids
            ]
        tabs[tabs_listname] = [
            group for group in groups
            if group.get(tabs_listname)
        ]
    else:
        tabs[tabs_listname] = [
            item for item in tabs[tabs_listname]
            if str(item["commontrack_id"]) not in remove_ids
        ]
    key = tab_key(user_id, tabs["tabs_id"])
    tab_cache_set(key, tabs)
    logger.info(
        "Removed %s items from %s",
        len(track_ids),
        tabs_listname,
    )
    return tabs


def stable_id(prefix: str, commontrack_id: int, name: str, evidence: str) -> str:
    name_norm = (name or "").strip().lower()
    evidence_norm = (evidence or "").strip().lower()
    raw = f"{commontrack_id}|{name_norm}|{evidence_norm}".encode("utf-8")
    return f"{prefix}_{hashlib.sha1(raw).hexdigest()[:16]}"


