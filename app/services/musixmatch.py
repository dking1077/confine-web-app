from dataclasses import dataclass
from app.errors import ApiError
import requests
import logging
import time


logger = logging.getLogger(__name__)


@dataclass
class ApiData:
    artist_name: str
    album_name: str
    track_name: str
    commontrack_id: int
    lyrics: str
    features: list

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            artist_name=data["artist_name"],
            commontrack_id=data["commontrack_id"],
            album_name=data["album_name"],
            track_name=data["track_name"],
            lyrics=data.get("lyrics"),
            features=data.get("features") or [],
        )

    def to_dict(self):
        return {
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "track_name": self.track_name,
            "commontrack_id": self.commontrack_id,
            "lyrics": self.lyrics,
            "features": self.features,
        }


class MusixMatch:
    def __init__(self, api_key):
        self.classes = []
        self.api_key = api_key
        self.base_url = "https://api.musixmatch.com/ws/1.1"
        self.timeout = 10
        self.max_attempts = 3

    def request_json(self, url, params=None, headers=None):
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                res = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers=headers
                )
                res.raise_for_status()
                return res.json()

            except requests.Timeout as err:
                last_error = err
                logger.warning("musixmatch timeout attempt=%s url=%s", attempt, url)

            except requests.RequestException as err:
                last_error = err
                logger.warning("musixmatch request failed attempt=%s url=%s error=%s", attempt, url, err)

            if attempt < self.max_attempts:
                time.sleep(attempt)

        raise ApiError(
            code="MUSIXMATCH_REQUEST_FAILED",
            message="Failed to fetch data from MusixMatch.",
            status_code=502,
            details={"error": str(last_error) if last_error else "unknown"},
        )

    def track_search(self, artist=None, track=None):
        logger.info("musixmatch api call - track search: artist=%s, track=%s", artist, track)
        classes = []
        search_params = {
            "apikey": self.api_key,
            "f_has_lyrics": 1,
            "s_track_rating": "desc",
            "page_size": 10,
            "page": 1,
            "s_track_language": "en",
            "f_lyrics_language": "en",
        }
        if artist:
            search_params["q_artist"] = artist
        if track:
            search_params["q_track"] = track
        headers = {"Accept-Language": "en-US,en;q=0.9"}
        search_url = f"{self.base_url}/track.search"
        res = self.request_json(search_url, params=search_params, headers=headers)
        tracks = res.get("message", {}).get("body", {}).get("track_list", [])
        for track in tracks:
            item = track.get("track", {})
            classes.append(
                ApiData(
                    artist_name=item.get("artist_name"),
                    commontrack_id=item.get("commontrack_id"),
                    album_name=item.get("album_name"),
                    track_name=item.get("track_name"),
                    lyrics="pending",
                    features=[],
                )
            )
        logger.info("api call succeeded: count=%s", len(classes))
        return classes

    def get_lyrics(self, track_id):
        search_url = f"{self.base_url}/track.lyrics.get"
        params_search = {
            "apikey": self.api_key,
            "commontrack_id": track_id,
        }
        res = self.request_json(search_url, params=params_search)
        status_code = res.get("message", {}).get("header", {}).get("status_code")
        if status_code == 404:
            logger.info("error status 404 - commontrack_id=%s", track_id)
        lyrics = (
            res.get("message", {}).get("body", {}).get("lyrics", {}).get("lyrics_body")
        )
        if lyrics == "":
            logger.info("return status 202 blank response - commontrack_id=%s", track_id)
        else:
            logger.info("lyrics fetched - commontrack_id=%s", track_id)
        return lyrics