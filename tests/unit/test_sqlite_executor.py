import sqlite3

import pytest

from university_qa.adapters.sqlite_executor import SqliteExecutor
from university_qa.domain.types import SqlExecutionError


@pytest.fixture()
def mem_conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE students (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            year INTEGER
        );
        INSERT INTO students VALUES (1, 'Alice', 2022);
        INSERT INTO students VALUES (2, 'Bob',   2023);
        INSERT INTO students VALUES (3, 'Carol',  2022);
    """)
    return c


@pytest.fixture()
def executor(mem_conn: sqlite3.Connection) -> SqliteExecutor:
    return SqliteExecutor(mem_conn)


def test_dialect_is_sqlite(executor: SqliteExecutor) -> None:
    assert executor.dialect == "sqlite"


def test_happy_path_returns_rows(executor: SqliteExecutor) -> None:
    rows = executor.run("SELECT id, name FROM students ORDER BY id")
    assert len(rows) == 3
    assert rows[0] == {"id": 1, "name": "Alice"}


def test_returns_list_of_dicts(executor: SqliteExecutor) -> None:
    rows = executor.run("SELECT * FROM students LIMIT 1")
    assert isinstance(rows, list)
    assert isinstance(rows[0], dict)


def test_empty_result_returns_empty_list(executor: SqliteExecutor) -> None:
    rows = executor.run("SELECT * FROM students WHERE year = 9999")
    assert rows == []


def test_filter_by_column(executor: SqliteExecutor) -> None:
    rows = executor.run("SELECT name FROM students WHERE year = 2022 ORDER BY name")
    names = [r["name"] for r in rows]
    assert names == ["Alice", "Carol"]


def test_aggregation(executor: SqliteExecutor) -> None:
    rows = executor.run("SELECT COUNT(*) AS cnt FROM students")
    assert rows[0]["cnt"] == 3


def test_syntax_error_raises_sql_execution_error(executor: SqliteExecutor) -> None:
    with pytest.raises(SqlExecutionError) as exc_info:
        executor.run("SELEKT * FROM students")
    assert exc_info.value.sql == "SELEKT * FROM students"


def test_bad_column_raises_sql_execution_error(executor: SqliteExecutor) -> None:
    with pytest.raises(SqlExecutionError):
        executor.run("SELECT nonexistent_col FROM students")


def test_from_path_opens_read_only(tmp_path: pytest.TempPathFactory) -> None:
    """SqliteExecutor.from_path must use read-only mode; INSERT must raise."""
    db_file = tmp_path / "test.db"  # type: ignore[operator]
    setup = sqlite3.connect(str(db_file))
    setup.executescript("CREATE TABLE t (x INTEGER); INSERT INTO t VALUES (1);")
    setup.close()

    executor = SqliteExecutor.from_path(db_file)
    # SELECT works
    rows = executor.run("SELECT * FROM t")
    assert rows == [{"x": 1}]

    # INSERT must be blocked by the read-only connection
    with pytest.raises(SqlExecutionError):
        executor.run("INSERT INTO t VALUES (2)")


def test_sql_attached_to_error(executor: SqliteExecutor) -> None:
    bad_sql = "SELECT * FROM nonexistent_table"
    with pytest.raises(SqlExecutionError) as exc_info:
        executor.run(bad_sql)
    assert exc_info.value.sql == bad_sql


def test_original_exception_preserved(executor: SqliteExecutor) -> None:
    with pytest.raises(SqlExecutionError) as exc_info:
        executor.run("SELECT * FROM no_such_table")
    assert exc_info.value.original is not None
    assert isinstance(exc_info.value.original, sqlite3.Error)
