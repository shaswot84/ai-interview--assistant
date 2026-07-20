"""OpenAI client factory — creates authenticated client instances from config."""

from openai import OpenAI

from config import config


def get_openai_client() -> OpenAI:
    """Return an OpenAI client configured with the current API key and base URL."""
    kwargs = {"api_key": config.openai_api_key}
    if config.openai_base_url:
        kwargs["base_url"] = config.openai_base_url
    return OpenAI(**kwargs)


def get_provider() -> str:
    """Return the configured LLM provider name (only 'openai' is supported)."""
    return config.llm_provider
