from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from university_qa.ports.tracer import Tracer


class NoopTracer(Tracer):
    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[None]:
        yield

    def event(self, name: str, **attributes: Any) -> None:
        pass
