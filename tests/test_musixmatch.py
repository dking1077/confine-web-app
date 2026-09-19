from requests.exceptions import Timeout
from app.errors import ApiError
from app.services import MusixMatch
from app.services.musixmatch import ApiData
import responses
import pytest


@pytest.fixture
def client():
    return MusixMatch(api_key="test_key")


@responses.activate
def test_track_search_success(client):
    """Test successful search and deserialization into ApiData objects."""
    responses.add(
        responses.GET,
        "https://api.musixmatch.com/ws/1.1/track.search",
        json={
            "message": {
                "body": {
                    "track_list": [
                        {
                            "track": {
                                "artist_name": "Radiohead",
                                "commontrack_id": 101,
                                "album_name": "OK Computer",
                                "track_name": "Karma Police",
                            }
                        }
                    ]
                }
            }
        },
        status=200,
    )

    results = client.track_search(artist="Radiohead")

    assert len(results) == 1
    assert isinstance(results[0], ApiData)
    assert results[0].track_name == "Karma Police"
    assert results[0].lyrics == "pending"


@responses.activate
def test_get_lyrics_success(client):
    """Test fetching lyrics for a given track ID."""
    responses.add(
        responses.GET,
        "https://api.musixmatch.com/ws/1.1/track.lyrics.get",
        json={
            "message": {
                "header": {"status_code": 200},
                "body": {"lyrics": {"lyrics_body": "Karma police, arrest this man"}},
            }
        },
        status=200,
    )

    lyrics = client.get_lyrics(track_id=101)
    assert lyrics == "Karma police, arrest this man"


@responses.activate
def test_get_lyrics_404_status(client):
    """Test handling when API header status_code is 404 (not found)."""
    responses.add(
        responses.GET,
        "https://api.musixmatch.com/ws/1.1/track.lyrics.get",
        json={
            "message": {
                "header": {"status_code": 404},
                "body": {},
            }
        },
        status=200,
    )

    lyrics = client.get_lyrics(track_id=999)
    assert lyrics is None


@responses.activate
def test_get_lyrics_blank_response(client):
    """Test handling when returned lyrics_body is empty string."""
    responses.add(
        responses.GET,
        "https://api.musixmatch.com/ws/1.1/track.lyrics.get",
        json={
            "message": {
                "header": {"status_code": 200},
                "body": {"lyrics": {"lyrics_body": ""}},
            }
        },
        status=200,
    )

    lyrics = client.get_lyrics(track_id=102)
    assert lyrics == ""


@responses.activate
def test_request_retry_and_api_error(client, monkeypatch):
    """Test retry behavior and eventual ApiError exception on failure."""
    client.max_attempts = 2
    monkeypatch.setattr("time.sleep", lambda secs: None)  # Bypass retry delays

    responses.add(
        responses.GET,
        "https://api.musixmatch.com/ws/1.1/track.search",
        body=Timeout("Connection timed out"),
    )

    with pytest.raises(ApiError) as exc_info:
        client.track_search(artist="Radiohead")

    assert exc_info.value.code == "MUSIXMATCH_REQUEST_FAILED"
    assert exc_info.value.status_code == 502
    assert len(responses.calls) == 2  # Verified retries occurred