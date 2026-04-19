"""Composition root — the ONLY file that imports both ports and adapters.

Adapter selection rules:
  - ANTHROPIC_API_KEY set → AnthropicLlmClient (preferred when both are set)
  - OPENAI_API_KEY set   → OpenAiLlmClient
  - Neither set          → RuntimeError (fail fast, clear message)
"""

from university_qa.adapters.sqlite_executor import SqliteExecutor
from university_qa.adapters.sqlite_schema import SqliteSchemaProvider
from university_qa.agent.graph import build_graph
from university_qa.agent.nodes import Dependencies
from university_qa.config import Settings


def _build_llm(settings: Settings):  # type: ignore[return]
    if settings.anthropic_api_key:
        from university_qa.adapters.anthropic_llm import AnthropicLlmClient

        return AnthropicLlmClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    if settings.openai_api_key:
        from university_qa.adapters.openai_llm import OpenAiLlmClient

        return OpenAiLlmClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    raise RuntimeError(
        "No LLM API key configured. "
        "Set ANTHROPIC_API_KEY (preferred) or OPENAI_API_KEY in your environment or .env file."
    )


def _build_tracer(settings: Settings):  # type: ignore[return]
    if settings.langsmith_tracing:
        import os

        from university_qa.adapters.langsmith_tracer import LangsmithTracer

        # LangGraph reads LANGSMITH_* from os.environ for auto-tracing; mirror
        # whatever was loaded from .env so the EU endpoint is picked up too.
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        if settings.langsmith_api_key:
            os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        if settings.langsmith_endpoint:
            os.environ.setdefault("LANGSMITH_ENDPOINT", settings.langsmith_endpoint)
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)

        return LangsmithTracer(
            project=settings.langsmith_project,
            api_url=settings.langsmith_endpoint,
        )

    from university_qa.adapters.noop_tracer import NoopTracer

    return NoopTracer()


def build_app(settings: Settings | None = None):  # type: ignore[return]
    """Wire all adapters and return a compiled LangGraph application."""
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    import sqlite3

    conn = sqlite3.connect(
        f"file:{settings.db_path}?mode=ro",
        uri=True,
        check_same_thread=False,
    )

    deps = Dependencies(
        schema_provider=SqliteSchemaProvider(conn),
        executor=SqliteExecutor(conn),
        llm=_build_llm(settings),
        tracer=_build_tracer(settings),
    )
    return build_graph(deps)
