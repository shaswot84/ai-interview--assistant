"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Runtime configuration values, all sourced from environment variables."""

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    question_timer_seconds: int = 180

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config by reading the .env file / environment."""
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv("OPENAI_BASE_URL", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            question_timer_seconds=int(os.getenv("QUESTION_TIMER_SECONDS", "180")),
        )


# Singleton config instance used throughout the application
config = Config.from_env()
