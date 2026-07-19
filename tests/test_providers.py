from openai import OpenAI

from providers import get_openai_client, get_provider


class TestGetOpenAIClient:
    def test_returns_openai_instance(self):
        client = get_openai_client()
        assert isinstance(client, OpenAI)


class TestGetProvider:
    def test_returns_string(self):
        provider = get_provider()
        assert isinstance(provider, str)
        assert provider == "openai"
