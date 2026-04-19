from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class Tracer(ABC):
    @contextmanager
    @abstractmethod
    def span(self, name: str, **attributes: Any) -> Iterator[None]: ...

    @abstractmethod
    def event(self, name: str, **attributes: Any) -> None: ...
