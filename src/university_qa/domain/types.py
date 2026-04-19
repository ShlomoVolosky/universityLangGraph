from dataclasses import dataclass, field
from typing import Any

Row = dict[str, Any]
QueryResult = list[Row]


@dataclass(frozen=True)
class SchemaDescription:
    text: str
    table_names: list[str] = field(default_factory=list)


class SqlExecutionError(Exception):
    def __init__(self, message: str, sql: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.sql = sql
        self.original = original
