import sqlite3
import time
from pathlib import Path

from university_qa.domain.types import QueryResult, SqlExecutionError
from university_qa.ports.sql_executor import SqlExecutor

_TIMEOUT_SECONDS = 5
_PROGRESS_OPCODES = 1000  # check roughly every N VM opcodes


class SqliteExecutor(SqlExecutor):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    @classmethod
    def from_path(cls, db_path: str | Path) -> "SqliteExecutor":
        path = str(db_path)
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        return cls(conn)

    @property
    def dialect(self) -> str:
        return "sqlite"

    def run(self, sql: str) -> QueryResult:
        deadline = time.monotonic() + _TIMEOUT_SECONDS
        timed_out = False

        def _progress() -> bool | None:
            nonlocal timed_out
            if time.monotonic() > deadline:
                timed_out = True
                return True  # interrupt
            return None

        self._conn.set_progress_handler(_progress, _PROGRESS_OPCODES)
        try:
            cur = self._conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
        except sqlite3.OperationalError as exc:
            if timed_out:
                raise SqlExecutionError("Query exceeded 5-second timeout.", sql, exc) from exc
            raise SqlExecutionError(str(exc), sql, exc) from exc
        except sqlite3.Error as exc:
            raise SqlExecutionError(str(exc), sql, exc) from exc
        finally:
            self._conn.set_progress_handler(None, 0)

        return [dict(row) for row in rows]
