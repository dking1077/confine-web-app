from marshmallow import Schema, fields, validate, EXCLUDE
import logging

logger = logging.getLogger(__name__)


class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(
        required=True,
        validate=validate.Length(min=8)
    )


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(
        required=True
    )


class SearchSchema(Schema):
    search_input = fields.String(
        required=True,
        validate=validate.Length(min=1)
    )


class AddToPanelSchema(Schema):
    items = fields.List(
        fields.Integer(),
        required=True
    )
    panel = fields.String(
        required=True,
        validate=validate.OneOf(["workspace", "concepts", "semantics"])
    )


class RemoveFromPanelSchema(Schema):
    items = fields.List(
        fields.String(),
        required=True
    )
    panel = fields.String(
        required=True,
        validate=validate.OneOf(["workspace", "concepts", "semantics"])
    )


class AnalyzeItemsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    items = fields.List(
        fields.Integer(),
        required=True
    )


class ProcessItemsSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    concept_ids = fields.List(
        fields.String(),
        required=True
    )
    semantic_ids = fields.List(
        fields.String(),
        required=True
    )
    instructions = fields.String(
        load_default=""
    )
    input_text = fields.String(
        load_default=""
    )


def validate_concepts(ai_client, tracks_lyrics):
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        concepts = ai_client.get_concepts(tracks_lyrics)

        if not isinstance(concepts, list) or len(concepts) != len(tracks_lyrics):
            logger.warning("invalid concepts schema on attempt=%s response=%r", attempt, concepts)
            continue

        valid = True
        for i, t in enumerate(concepts):
            if not (
                isinstance(t, dict)
                and "commontrack_id" in t
                and "track" in t
                and isinstance(t.get("concepts"), list)
            ):
                logger.warning(
                    "invalid concepts item attempt=%s index=%s item=%r", attempt, i, t,
                )
                valid = False
                break

        if valid:
            return concepts
        return None


def validate_semantics(ai_client, tracks_lyrics):
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        semantics = ai_client.get_semantics(tracks_lyrics)

        if not isinstance(semantics, list) or len(semantics) != len(tracks_lyrics):
            logger.warning("invalid semantics schema on attempt=%s response=%r", attempt, semantics)
            continue

        valid = True
        for i, t in enumerate(semantics):
            if not (
                isinstance(t, dict)
                and "commontrack_id" in t
                and "track" in t
                and isinstance(t.get("semantics"), list)
            ):
                logger.warning(
                    "invalid semantics item attempt=%s index=%s item=%r", attempt, i, t,
                )
                valid = False
                break

        if valid:
            return semantics
        return None