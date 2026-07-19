from openai import OpenAI

from config import config


def get_openai_client() -> OpenAI:
    kwargs = {"api_key": config.openai_api_key}
    if config.openai_base_url:
        kwargs["base_url"] = config.openai_base_url
    return OpenAI(**kwargs)


def get_provider() -> str:
    return config.llm_provider
