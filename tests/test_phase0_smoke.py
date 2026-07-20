"""Smoke tests — verify API key presence, provider configuration, and a basic LLM round-trip."""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def _key_is_placeholder(key: str | None) -> bool:
    """Return True if the API key is missing or set to a placeholder value."""
    if not key:
        return True
    key = key.strip()
    if key in ("", "sk-...", "gsk-...", "OPENAI_API_KEY"):
        return True
    return False


def test_api_key_exists():
    """The OPENAI_API_KEY environment variable must be set."""
    key = os.getenv("OPENAI_API_KEY")
    assert not _key_is_placeholder(key), (
        "OPENAI_API_KEY is not set or is placeholder"
    )


def test_llm_provider_default():
    """Only 'openai' is supported as the LLM provider."""
    provider = os.getenv("LLM_PROVIDER", "openai")
    assert provider == "openai", (
        f"LLM_PROVIDER must be 'openai' (the only supported provider), got {provider}"
    )


@pytest.mark.skipif(
    _key_is_placeholder(os.getenv("OPENAI_API_KEY")),
    reason="OpenAI API key not configured",
)
def test_openai_round_trip():
    """A minimal chat completion call should succeed."""
    from openai import OpenAI

    base_url = os.getenv("OPENAI_BASE_URL")
    kwargs = {}
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": "Say hello in one word"}],
        max_tokens=10,
    )
    content = response.choices[0].message.content
    assert content is not None and len(content) > 0
