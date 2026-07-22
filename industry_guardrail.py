"""Industry validation guardrail using an Ollama LLM classifier."""

import json
import logging
import re

from openai import APIError, RateLimitError

from config import config
from providers import get_ollama_client

logger = logging.getLogger(__name__)


def _parse_boolean_response(text: str | None) -> bool | None:
    """Extract a boolean `is_valid` value from model output.

    Tries strict JSON parsing first, falls back to a regex search for
    ``"is_valid": true|false`` anywhere in the text.
    """
    if text is None:
        return None
    try:
        data = json.loads(text)
        return bool(data["is_valid"])
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    m = re.search(r'"is_valid"\s*:\s*(true|false)', text, re.IGNORECASE)
    if m:
        return m.group(1).lower() == "true"
    return None


def validate_industry(input_text: str) -> bool:
    """Use Ollama to determine whether *input_text* is a valid industry.

    Returns ``True`` if the model classifies the text as a valid industry
    (e.g. FinTech, Healthcare, Education), ``False`` otherwise.  Never
    exposes the model's reasoning to the caller.

    Raises ``RuntimeError`` if the API call fails so the caller can
    surface a friendly error and let the user retry.
    """
    logger.info("validate_industry input: %r", input_text)
    if not config.ollama_api_key:
        raise RuntimeError("Ollama API key is not configured.")
    client = get_ollama_client()
    prompt = (
        "You are a classifier that determines whether the given input is a "
        "valid industry or industry domain. Respond with ONLY valid JSON. "
        "No other text, no explanation, no markdown formatting.\n\n"
        'Valid industries include e.g. FinTech, Healthcare, Education, Retail, '
        'Manufacturing, E-commerce, Cybersecurity, Agriculture, Energy.\n\n'
        'Invalid inputs include e.g. "hello", "I do not know", "banana", '
        '"Backend Engineer", "12345", random sentences, questions, code, emojis.\n\n'
        "The response must be exactly one of the following (without backticks):\n"
        '{"is_valid": true}\n'
        '{"is_valid": false}'
    )
    try:
        response = client.chat.completions.create(
            model=config.ollama_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": input_text},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        logger.info("Ollama raw response: %r", content)
        parsed = _parse_boolean_response(content)
        if parsed is None:
            logger.error("Failed to parse boolean from response: %r", content)
            raise ValueError(f"Could not parse boolean from Ollama response: {content}")
        logger.info("Parsed result: %s", parsed)
        return parsed
    except (APIError, RateLimitError, ValueError) as e:
        logger.exception("Industry validation failed")
        raise RuntimeError(f"Industry validation failed: {e}") from e
