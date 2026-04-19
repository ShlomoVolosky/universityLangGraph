from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from university_qa.agent.nodes import (
    Dependencies,
    execute_sql,
    format_answer,
    load_schema,
    validate_sql,
)
from university_qa.agent.nodes import generate_sql as _generate_sql
from university_qa.agent.router import (
    reject_non_select_node,
    retry_or_fail_node,
    route_after_execution,
    route_after_retry,
    route_after_validation,
)
from university_qa.domain.state import AgentState


def build_graph(deps: Dependencies) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Return a compiled LangGraph application wired to the given dependencies."""

    # Bind deps to each node via closures — LangGraph nodes take only state.
    def _load_schema(state: AgentState) -> dict[str, object]:
        return load_schema(state, deps)

    def _gen_sql(state: AgentState) -> dict[str, object]:
        return _generate_sql(state, deps)

    def _validate_sql(state: AgentState) -> dict[str, object]:
        return validate_sql(state, deps)

    def _execute_sql(state: AgentState) -> dict[str, object]:
        return execute_sql(state, deps)

    def _format_answer(state: AgentState) -> dict[str, object]:
        return format_answer(state, deps)

    def _retry_or_fail(state: AgentState) -> dict[str, object]:
        return retry_or_fail_node(state, deps)

    def _reject_non_select(state: AgentState) -> dict[str, object]:
        return reject_non_select_node(state, deps)

    g: StateGraph[Any, Any, Any] = StateGraph(AgentState)

    g.add_node("load_schema", _load_schema)
    g.add_node("generate_sql", _gen_sql)
    g.add_node("validate_sql", _validate_sql)
    g.add_node("execute_sql", _execute_sql)
    g.add_node("format_answer", _format_answer)
    g.add_node("retry_or_fail", _retry_or_fail)
    g.add_node("reject_non_select", _reject_non_select)

    g.add_edge(START, "load_schema")
    g.add_edge("load_schema", "generate_sql")
    g.add_edge("generate_sql", "validate_sql")

    g.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "execute_sql": "execute_sql",
            "retry_or_fail": "retry_or_fail",
            "reject_non_select": "reject_non_select",
        },
    )

    g.add_conditional_edges(
        "execute_sql",
        route_after_execution,
        {
            "format_answer": "format_answer",
            "retry_or_fail": "retry_or_fail",
        },
    )

    g.add_conditional_edges(
        "retry_or_fail",
        route_after_retry,
        {
            "generate_sql": "generate_sql",
            END: END,
        },
    )

    g.add_edge("format_answer", END)
    g.add_edge("reject_non_select", END)

    return g.compile()
