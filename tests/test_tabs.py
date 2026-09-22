from unittest.mock import MagicMock
import pytest
from flask_jwt_extended import create_access_token


def get_auth_headers(app, user_id=1):
    """Generate JWT headers directly using Flask-JWT-Extended without route calls."""
    with app.app_context():
        token = create_access_token(identity=str(user_id))
        return {"Authorization": f"Bearer {token}"}


# --- UNAUTHORIZED ACCESS ---

@pytest.mark.parametrize(
    "endpoint",
    [
        "/tabs/add_to_panel",
        "/tabs/remove_from_panel",
        "/tabs/analyze_items",
        "/tabs/process_items",
    ],
)
def test_tabs_unauthorized(client, endpoint):
    """Verify endpoints require authentication."""
    res = client.post(endpoint, json={})
    assert res.status_code == 401


# --- ADD TO PANEL ---

def test_add_to_panel_success(client, app, monkeypatch):
    headers = get_auth_headers(app)

    monkeypatch.setattr(
        "app.tabs.routes.resolve_by_id",
        lambda uid, ids, panel: [{"commontrack_id": 101}],
    )
    monkeypatch.setattr(
        "app.tabs.routes.fetch_lyrics",
        lambda items: items,
    )
    monkeypatch.setattr(
        "app.tabs.routes.append_tabs_list",
        lambda uid, items, panel: {"workspace": items},
    )

    # items: List[Integer], panel: "workspace" | "concepts" | "semantics"
    payload = {
        "items": [101],
        "panel": "workspace",
    }

    res = client.post("/tabs/add_to_panel", json=payload, headers=headers)
    assert res.status_code == 200


# --- REMOVE FROM PANEL ---

def test_remove_from_panel_success(client, app, monkeypatch):
    headers = get_auth_headers(app)

    monkeypatch.setattr(
        "app.tabs.routes.remove_tabs_list",
        lambda uid, ids, panel: {"workspace": []},
    )

    # items: List[String] (Must be strings according to RemoveFromPanelSchema!)
    payload = {
        "items": ["101"],
        "panel": "workspace",
    }

    res = client.post("/tabs/remove_from_panel", json=payload, headers=headers)
    assert res.status_code == 200


# --- ANALYZE ITEMS ---

def test_analyze_items_success(client, app, monkeypatch):
    headers = get_auth_headers(app)

    monkeypatch.setattr(
        "app.tabs.routes.resolve_by_id",
        lambda uid, ids, panel=None: [
            {
                "commontrack_id": 101,
                "track_name": "Karma Police",
                "lyrics": "Karma police...",
            }
        ],
    )

    mock_task_result = MagicMock()
    mock_concepts = [
        {
            "track": "Karma Police",
            "commontrack_id": 101,
            "concepts": [
                {
                    "id": "c1",
                    "name": "Isolation",
                    "display_concept": "Isolation Concept",
                    "evidence": "Karma police...",
                }
            ],
        }
    ]
    mock_semantics = [
        {
            "track": "Karma Police",
            "commontrack_id": 101,
            "semantics": [
                {
                    "id": "s1",
                    "name": "Dystopian",
                    "display_semantic": "Dystopian Theme",
                    "evidence": "Karma police...",
                }
            ],
        }
    ]
    mock_task_result.get.return_value = (mock_concepts, mock_semantics)

    monkeypatch.setattr(
        "app.tabs.routes.analyze_items_task.delay",
        lambda tracks: mock_task_result,
    )

    monkeypatch.setattr(
        "app.tabs.routes.append_tabs_list",
        lambda uid, items, panel: {
            "concepts": mock_concepts,
            "semantics": mock_semantics,
        },
    )

    # items: List[Integer]
    payload = {
        "items": [101],
    }

    res = client.post("/tabs/analyze_items", json=payload, headers=headers)
    assert res.status_code == 200


# --- PROCESS ITEMS ---

def test_process_items_success(client, app, monkeypatch):
    headers = get_auth_headers(app)

    monkeypatch.setattr(
        "app.tabs.routes.resolve_by_id",
        lambda uid, ids, panel=None: [{"id": i} for i in ids],
    )

    mock_task_result = MagicMock()
    mock_task_result.get.return_value = "Processed output text"

    monkeypatch.setattr(
        "app.tabs.routes.process_input.delay",
        lambda concepts, semantics, instructions, input_text: mock_task_result,
    )

    # concept_ids: List[String], semantic_ids: List[String]
    payload = {
        "concept_ids": ["c1"],
        "semantic_ids": ["s1"],
        "instructions": "Summarize themes",
        "input_text": "Sample context",
    }

    res = client.post("/tabs/process_items", json=payload, headers=headers)
    assert res.status_code == 200