from app.prompts import classify_search_messages, classify_concepts_message
from app.prompts import transform_lyrics_messages, classify_semantics_message
from app.errors import ApiError
from openai import OpenAI
import logging
import json
import re
import time


logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.max_attempts = 3
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=0,
        )

    def create_completion(self, messages):
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0,
                    max_tokens=1200
                )
                return response

            except Exception as err:
                last_error = err
                logger.warning("openrouter request failed attempt=%s error=%s", attempt, err)

            if attempt < self.max_attempts:
                time.sleep(attempt)

        raise ApiError(
            code="OPENROUTER_REQUEST_FAILED",
            message="Failed to fetch data from OpenRouter.",
            status_code=502,
            details={"error": str(last_error) if last_error else "unknown"},
        )

    def parse_json_response(self, content):
        res = re.sub(r"^```(?:json)?\s*", "", content.strip())
        res = re.sub(r"\s*```$", "", res.strip())

        try:
            return json.loads(res)
        except json.JSONDecodeError:
            raise ApiError(
                code="AI_INVALID_RESPONSE",
                message="AI service returned invalid JSON.",
                status_code=502,
            )

    def parse_search(self, search):
        messages = classify_search_messages(search)
        response = self.create_completion(messages)
        search_params = self.parse_json_response(response.choices[0].message.content)

        artist_input = search_params['artist']
        track_input = search_params['track']

        if track_input == 'None':
            track_input = None
        return artist_input, track_input

    def get_concepts(self, track_lyrics):
        messages = classify_concepts_message(track_lyrics)
        response = self.create_completion(messages)
        return self.parse_json_response(response.choices[0].message.content)

    def get_semantics(self, track_lyrics):
        messages = classify_semantics_message(track_lyrics)
        response = self.create_completion(messages)
        return self.parse_json_response(response.choices[0].message.content)

    def transform_lyrics(self, lyrics, selected_concepts, selected_semantics, user_instructions=None):
        messages = transform_lyrics_messages(
            lyrics=lyrics,
            selected_concepts=selected_concepts,
            selected_semantics=selected_semantics,
            user_instructions=user_instructions,
        )
        response = self.create_completion(messages)
        res = response.choices[0].message.content
        res = re.sub(r"^```(?:json)?\s*", "", res.strip())
        res = re.sub(r"\s*```$", "", res.strip())
        return res