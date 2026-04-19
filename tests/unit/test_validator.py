"""Exhaustive tests for the SQL validator — a security boundary."""

from university_qa.agent.validator import ValidationResult, validate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ok(sql: str) -> ValidationResult:
    return validate(sql, dialect="sqlite")


def bad(sql: str) -> ValidationResult:
    return validate(sql, dialect="sqlite")


# ---------------------------------------------------------------------------
# Accepted cases
# ---------------------------------------------------------------------------


def test_simple_select_accepted() -> None:
    result = ok("SELECT 1")
    assert result.ok is True
    assert result.errors == []
    assert result.is_non_select is False


def test_select_from_table_accepted() -> None:
    result = ok("SELECT id, name FROM students")
    assert result.ok is True


def test_select_with_where_accepted() -> None:
    result = ok("SELECT * FROM students WHERE enrollment_year = 2022")
    assert result.ok is True


def test_aggregation_accepted() -> None:
    result = ok("SELECT AVG(grade) FROM enrollments")
    assert result.ok is True


def test_join_accepted() -> None:
    result = ok(
        "SELECT s.name, AVG(e.grade) "
        "FROM students s "
        "JOIN enrollments e ON s.id = e.student_id "
        "GROUP BY s.id"
    )
    assert result.ok is True


def test_subquery_accepted() -> None:
    result = ok("SELECT * FROM (SELECT id FROM students WHERE enrollment_year = 2023) sub")
    assert result.ok is True


def test_cte_accepted() -> None:
    result = ok(
        "WITH recent AS (SELECT * FROM students WHERE enrollment_year = 2024) SELECT * FROM recent"
    )
    assert result.ok is True


def test_window_function_accepted() -> None:
    result = ok(
        "SELECT student_id, grade, "
        "RANK() OVER (PARTITION BY offering_id ORDER BY grade DESC) AS rnk "
        "FROM enrollments"
    )
    assert result.ok is True


def test_order_by_limit_accepted() -> None:
    result = ok("SELECT name FROM students ORDER BY name DESC LIMIT 5")
    assert result.ok is True


def test_multi_table_join_accepted() -> None:
    result = ok(
        "SELECT t.name, c.title, co.semester "
        "FROM teachers t "
        "JOIN course_offerings co ON t.id = co.teacher_id "
        "JOIN courses c ON co.course_id = c.id "
        "WHERE co.semester = '2024-Fall'"
    )
    assert result.ok is True


def test_case_expression_accepted() -> None:
    result = ok(
        "SELECT name, CASE WHEN enrollment_year < 2023 THEN 'senior' ELSE 'junior' END "
        "FROM students"
    )
    assert result.ok is True


def test_count_star_accepted() -> None:
    result = ok("SELECT COUNT(*) AS total FROM enrollments")
    assert result.ok is True


# ---------------------------------------------------------------------------
# Rejected: non-SELECT roots
# ---------------------------------------------------------------------------


def test_insert_rejected_as_non_select() -> None:
    result = bad("INSERT INTO students (name, enrollment_year) VALUES ('Eve', 2025)")
    assert result.ok is False
    assert result.is_non_select is True


def test_update_rejected_as_non_select() -> None:
    result = bad("UPDATE students SET enrollment_year = 2025 WHERE id = 1")
    assert result.ok is False
    assert result.is_non_select is True


def test_delete_rejected_as_non_select() -> None:
    result = bad("DELETE FROM students WHERE id = 1")
    assert result.ok is False
    assert result.is_non_select is True


def test_drop_table_rejected_as_non_select() -> None:
    result = bad("DROP TABLE students")
    assert result.ok is False
    assert result.is_non_select is True


def test_create_table_rejected_as_non_select() -> None:
    result = bad("CREATE TABLE foo (id INTEGER)")
    assert result.ok is False
    assert result.is_non_select is True


def test_alter_table_rejected_as_non_select() -> None:
    result = bad("ALTER TABLE students ADD COLUMN email TEXT")
    assert result.ok is False
    assert result.is_non_select is True


def test_attach_database_rejected_as_non_select() -> None:
    result = bad('ATTACH DATABASE "/tmp/evil.db" AS evil')
    assert result.ok is False
    assert result.is_non_select is True


def test_pragma_rejected_as_non_select() -> None:
    result = bad("PRAGMA journal_mode=WAL")
    assert result.ok is False
    assert result.is_non_select is True


# ---------------------------------------------------------------------------
# Rejected: forbidden functions
# ---------------------------------------------------------------------------


def test_load_extension_rejected() -> None:
    result = bad("SELECT load_extension('evil.so')")
    assert result.ok is False
    assert any("load_extension" in e for e in result.errors)
    assert result.is_non_select is False


def test_readfile_rejected() -> None:
    result = bad("SELECT readfile('/etc/passwd')")
    assert result.ok is False
    assert any("readfile" in e for e in result.errors)


def test_writefile_rejected() -> None:
    result = bad("SELECT writefile('/tmp/out', 'data')")
    assert result.ok is False
    assert any("writefile" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Rejected: syntax errors
# ---------------------------------------------------------------------------


def test_syntax_error_rejected() -> None:
    result = bad("SELEKT * FORM students")
    assert result.ok is False
    assert result.is_non_select is False
    assert result.errors != []


def test_empty_string_rejected() -> None:
    result = bad("")
    assert result.ok is False


# ---------------------------------------------------------------------------
# Edge cases: is_non_select flag drives retry suppression
# ---------------------------------------------------------------------------


def test_is_non_select_false_for_syntax_error() -> None:
    """Syntax errors are retryable; is_non_select must be False."""
    result = bad("SELECT * FORM students")
    assert result.is_non_select is False


def test_is_non_select_true_for_ddl() -> None:
    result = bad("DROP TABLE enrollments")
    assert result.is_non_select is True


def test_validation_result_dataclass_fields() -> None:
    r = ValidationResult(ok=True)
    assert r.errors == []
    assert r.is_non_select is False
