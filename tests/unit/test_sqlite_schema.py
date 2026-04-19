import sqlite3

import pytest

from university_qa.adapters.sqlite_schema import SqliteSchemaProvider


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript("""
        CREATE TABLE teachers (
            id         INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            department TEXT
        );
        CREATE TABLE courses (
            id      INTEGER PRIMARY KEY,
            title   TEXT NOT NULL,
            credits INTEGER NOT NULL
        );
        CREATE TABLE enrollments (
            id         INTEGER PRIMARY KEY,
            teacher_id INTEGER NOT NULL REFERENCES teachers(id),
            course_id  INTEGER NOT NULL REFERENCES courses(id),
            grade      REAL
        );
    """)
    return c


def test_describe_returns_schema_description(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    result = provider.describe()
    assert result.text.startswith("Dialect: sqlite")


def test_table_names_listed(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    result = provider.describe()
    assert set(result.table_names) == {"teachers", "courses", "enrollments"}


def test_columns_appear_in_text(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    text = provider.describe().text
    assert "teachers" in text
    assert "name TEXT NOT NULL" in text
    assert "department TEXT" in text


def test_primary_key_annotated(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    text = provider.describe().text
    assert "id INTEGER PK" in text


def test_foreign_keys_appear_in_relationships(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    text = provider.describe().text
    assert "Relationships:" in text
    assert "enrollments.teacher_id -> teachers.id" in text
    assert "enrollments.course_id -> courses.id" in text


def test_result_is_cached(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    first = provider.describe()
    second = provider.describe()
    assert first is second


def test_refresh_clears_cache(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    first = provider.describe()
    provider.refresh()
    second = provider.describe()
    assert first is not second
    assert first.text == second.text


def test_dialect_line_present(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    lines = provider.describe().text.splitlines()
    assert lines[0] == "Dialect: sqlite"


def test_tables_section_header_present(conn: sqlite3.Connection) -> None:
    provider = SqliteSchemaProvider(conn)
    assert "Tables:" in provider.describe().text
