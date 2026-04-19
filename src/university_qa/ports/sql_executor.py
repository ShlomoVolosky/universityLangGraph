from abc import ABC, abstractmethod

from university_qa.domain.types import QueryResult


class SqlExecutor(ABC):
    @abstractmethod
    def run(self, sql: str) -> QueryResult: ...

    @property
    @abstractmethod
    def dialect(self) -> str: ...
