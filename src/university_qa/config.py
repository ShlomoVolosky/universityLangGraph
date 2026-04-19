from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM provider keys — at least one must be set; Anthropic preferred when both present
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # Database
    db_path: str = "db/university.db"

    # Agent
    max_attempts: int = 3

    # LangSmith tracing
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "university-qa-dev"

    model_config = {"env_file": ".env", "extra": "ignore"}
