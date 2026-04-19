from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from university_qa.ports.tracer import Tracer


class LangsmithTracer(Tracer):
    """Wraps custom spans/events via langsmith.Client.

    LangGraph auto-tracing covers node-level spans; this tracer adds
    custom metric spans (schema fetch, validation results, retry counts).
    """

    def __init__(self, project: str | None = None) -> None:
        from langsmith import Client

        self._client = Client()
        self._project = project

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[None]:
        # LangGraph handles node-level spans automatically; this records
        # additional sub-spans via a run tree when a parent run is active.
        try:
            from langsmith.run_helpers import get_current_run_tree

            parent = get_current_run_tree()
        except Exception:
            parent = None

        if parent is not None:
            child = parent.create_child(
                name=name,
                run_type="chain",
                inputs=attributes,
            )
            child.post()
            try:
                yield
            finally:
                child.end()
                child.patch()
        else:
            yield

    def event(self, name: str, **attributes: Any) -> None:
        try:
            from langsmith.run_helpers import get_current_run_tree

            run = get_current_run_tree()
            if run is not None:
                run.add_event({"name": name, "kwargs": attributes})
        except Exception:
            pass
