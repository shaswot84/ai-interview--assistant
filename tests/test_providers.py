"""Tests for the OpenAI client factory and provider identification."""

from openai import OpenAI

from providers import get_openai_client, get_provider


class TestGetOpenAIClient:
    """get_openai_client should return an OpenAI SDK instance."""

    def test_returns_openai_instance(self):
        client = get_openai_client()
        assert isinstance(client, OpenAI)


class TestGetProvider:
    """get_provider should return the provider name string."""

    def test_returns_string(self):
        provider = get_provider()
        assert isinstance(provider, str)
        assert provider == "openai"
