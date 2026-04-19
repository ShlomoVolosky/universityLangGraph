import json
import re
from dataclasses import dataclass

from university_qa.agent.prompts import (
    FORMAT_ANSWER_SYSTEM,
    GENERATE_SQL_SYSTEM,
    build_format_answer_user,
    build_generate_sql_user,
)
from university_qa.agent.validator import validate
from university_qa.domain.state import AgentState
from university_qa.ports.llm_client import LlmClient
from university_qa.ports.schema_provider import SchemaProvider
from university_qa.ports.sql_executor import SqlExecutor
from university_qa.ports.tracer import Tracer

_FENCE_RE = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_MAX_FORMAT_ROWS = 50
_NO_RESULTS_MSG = "No matching records were found for that question."


@dataclass
class Dependencies:
    schema_provider: SchemaProvider
    executor: SqlExecutor
    llm: LlmClient
    tracer: Tracer


def _strip_fences(text: str) -> str:
    m = _FENCE_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def load_schema(state: AgentState, deps: Dependencies) -> dict[str, object]:
    with deps.tracer.span("schema.fetch"):
        desc = deps.schema_provider.describe()
        deps.tracer.event(
            "schema.fetch",
            table_count=len(desc.table_names),
            total_column_count=desc.text.count(",") + len(desc.table_names),
        )
    return {"schema_snippet": desc.text}


def generate_sql(state: AgentState, deps: Dependencies) -> dict[str, object]:
    system = GENERATE_SQL_SYSTEM.format(
        dialect=deps.executor.dialect,
        schema=state.schema_snippet or "",
    )
    user = build_generate_sql_user(state.question, state.prior_attempts)
    sql = _strip_fences(deps.llm.complete(system=system, user=user))
    return {
        "generated_sql": sql,
        "attempts": state.attempts + 1,
        "validation_errors": [],
        "execution_error": None,
        "rows": None,
    }


def validate_sql(state: AgentState, deps: Dependencies) -> dict[str, object]:
    result = validate(state.generated_sql or "", dialect=deps.executor.dialect)
    with deps.tracer.span("sql.validate"):
        deps.tracer.event(
            "sql.validate",
            ok=result.ok,
            is_non_select=result.is_non_select,
            error_count=len(result.errors),
        )
    return {"validation_errors": result.errors}


def execute_sql(state: AgentState, deps: Dependencies) -> dict[str, object]:
    import time

    from university_qa.domain.types import SqlExecutionError

    sql = state.generated_sql or ""
    t0 = time.monotonic()
    try:
        with deps.tracer.span("sql.execute"):
            rows = deps.executor.run(sql)
            duration_ms = int((time.monotonic() - t0) * 1000)
            deps.tracer.event(
                "sql.execute",
                row_count=len(rows),
                duration_ms=duration_ms,
                succeeded=True,
            )
        return {"rows": rows, "execution_error": None}
    except SqlExecutionError as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        deps.tracer.event(
            "sql.execute",
            row_count=0,
            duration_ms=duration_ms,
            succeeded=False,
        )
        err = str(exc)
        return {
            "execution_error": err,
            "prior_attempts": state.prior_attempts + [(sql, err)],
        }


def format_answer(state: AgentState, deps: Dependencies) -> dict[str, object]:
    rows = state.rows or []
    if not rows:
        deps.tracer.event("answer.format", input_row_count=0, truncated=False)
        return {"answer": _NO_RESULTS_MSG, "terminal_reason": "ok"}

    truncated = len(rows) > _MAX_FORMAT_ROWS
    display_rows = rows[:_MAX_FORMAT_ROWS]
    rows_json = json.dumps(display_rows, default=str)

    with deps.tracer.span("answer.format"):
        deps.tracer.event(
            "answer.format",
            input_row_count=len(rows),
            truncated=truncated,
        )
        user = build_format_answer_user(state.question, rows_json, truncated, total_rows=len(rows))
        answer = deps.llm.complete(system=FORMAT_ANSWER_SYSTEM, user=user)

    return {"answer": answer, "terminal_reason": "ok"}
