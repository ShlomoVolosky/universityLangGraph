from pydantic import BaseModel, Field


class AgentState(BaseModel):
    # Input
    question: str

    # Schema context
    schema_snippet: str | None = None

    # SQL pipeline
    generated_sql: str | None = None
    validation_errors: list[str] = Field(default_factory=list)

    # Execution
    rows: list[dict[str, object]] | None = None
    execution_error: str | None = None

    # Control
    attempts: int = 0
    max_attempts: int = 3

    # History for retry prompts — list of (sql, error) tuples from prior attempts
    prior_attempts: list[tuple[str, str]] = Field(default_factory=list)

    # Output
    answer: str | None = None

    # Terminal reason — one of: "ok", "validation_failed",
    # "execution_failed", "exhausted_retries", "rejected_non_select"
    terminal_reason: str | None = None
