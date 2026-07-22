"""Client factories — creates authenticated OpenAI / Ollama client instances."""

from openai import OpenAI

from config import config


def get_openai_client() -> OpenAI:
    """Return an OpenAI client configured with the current API key and base URL."""
    kwargs = {"api_key": config.openai_api_key}
    if config.openai_base_url:
        kwargs["base_url"] = config.openai_base_url
    return OpenAI(**kwargs)


def get_ollama_client() -> OpenAI:
    """Return an OpenAI-compatible client configured for an Ollama endpoint."""
    kwargs = {"api_key": config.ollama_api_key}
    if config.ollama_base_url:
        kwargs["base_url"] = config.ollama_base_url
    return OpenAI(**kwargs)


def get_provider() -> str:
    """Return the configured LLM provider name (only 'openai' is supported)."""
    return config.llm_provider
