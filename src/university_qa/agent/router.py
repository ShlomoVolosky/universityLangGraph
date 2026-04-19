from langgraph.graph import END

from university_qa.agent.nodes import Dependencies
from university_qa.domain.state import AgentState

_EXHAUSTED_MSG = (
    "I couldn't produce a valid query for this question after {n} tries. Last error: {error}"
)
_REJECTED_MSG = (
    "I can only answer questions using SELECT queries. "
    "That request would require a data-modification statement, which is not allowed."
)


# ---------------------------------------------------------------------------
# Conditional edge functions (return node name strings)
# ---------------------------------------------------------------------------


def route_after_validation(state: AgentState) -> str:
    if not state.validation_errors:
        return "execute_sql"
    # Check if the validator flagged a non-SELECT (no retry)
    # We need to inspect the error to detect the non-select flag;
    # the flag is carried via the state — but validation_errors is just strings.
    # We re-run validate to get the flag (it's cheap and stateless).
    from university_qa.agent.validator import validate

    result = validate(state.generated_sql or "")
    if result.is_non_select:
        return "reject_non_select"
    return "retry_or_fail"


def route_after_execution(state: AgentState) -> str:
    if state.execution_error is None:
        return "format_answer"
    return "retry_or_fail"


def route_after_retry(state: AgentState) -> str:
    if state.terminal_reason is not None:
        return END
    return "generate_sql"


# ---------------------------------------------------------------------------
# Gate nodes (live here per brief: "keep this logic in router.py")
# ---------------------------------------------------------------------------


def retry_or_fail_node(state: AgentState, deps: Dependencies) -> dict[str, object]:
    updates: dict[str, object] = {}

    # If arriving from a validation failure, record it in prior_attempts.
    # (Execution failures are already recorded by execute_sql itself.)
    if state.validation_errors and state.generated_sql:
        error_msg = "; ".join(state.validation_errors)
        updates["prior_attempts"] = state.prior_attempts + [(state.generated_sql, error_msg)]
        updates["validation_errors"] = []

    last_error = state.execution_error or (
        "; ".join(state.validation_errors) if state.validation_errors else "unknown error"
    )

    if state.attempts >= state.max_attempts:
        updates["terminal_reason"] = "exhausted_retries"
        updates["answer"] = _EXHAUSTED_MSG.format(n=state.max_attempts, error=last_error)
        deps.tracer.event("terminal", terminal_reason="exhausted_retries", error=last_error)
    else:
        deps.tracer.event("retry", attempt=state.attempts, last_error=last_error)

    return updates


def reject_non_select_node(state: AgentState, deps: Dependencies) -> dict[str, object]:
    deps.tracer.event("terminal", terminal_reason="rejected_non_select")
    return {"terminal_reason": "rejected_non_select", "answer": _REJECTED_MSG}
