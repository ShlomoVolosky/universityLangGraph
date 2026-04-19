"""Integration tests — happy path. All run against in-memory SQLite + FakeLlmClient."""

from university_qa.adapters.fake_llm import FakeLlmClient

# Helper: FakeLlmClient needs 'Query results' matched first so format_answer
# doesn't accidentally consume a SQL pattern that also appears in the question.
_FMT = "Query results"


def _llm(sql: str, answer: str) -> FakeLlmClient:
    return FakeLlmClient({_FMT: answer, "": sql})


# ---------------------------------------------------------------------------
# 1. Single-table: count
# ---------------------------------------------------------------------------


def test_student_count(test_graph, fake_llm):
    llm = FakeLlmClient(
        {
            _FMT: "There are 5 students.",
            "students": "SELECT COUNT(*) AS cnt FROM students",
        }
    )
    result = test_graph(llm).invoke({"question": "How many students are there?"})
    assert result["terminal_reason"] == "ok"
    assert result["attempts"] == 1
    assert "5" in result["answer"]


# ---------------------------------------------------------------------------
# 2. Single-table with filter: credits
# ---------------------------------------------------------------------------


def test_course_credits(test_graph, fake_llm):
    llm = FakeLlmClient(
        {
            _FMT: "MA201: Calculus I has 4 credits.",
            "credits": "SELECT title, credits FROM courses ORDER BY credits DESC LIMIT 1",
        }
    )
    result = test_graph(llm).invoke({"question": "Which course has the most credits?"})
    assert result["terminal_reason"] == "ok"
    assert result["attempts"] == 1
    rows = result["rows"]
    assert rows is not None and len(rows) >= 1
    assert rows[0]["credits"] == 4


# ---------------------------------------------------------------------------
# 3. Two-table join: average grade in CS101 Fall 2024
# ---------------------------------------------------------------------------


def test_avg_grade_cs101_fall(test_graph):
    sql = (
        "SELECT AVG(e.grade) AS avg_grade "
        "FROM enrollments e "
        "JOIN course_offerings co ON e.offering_id = co.id "
        "JOIN courses c ON co.course_id = c.id "
        "WHERE c.title LIKE 'CS101%' AND co.semester = '2024-Fall'"
    )
    llm = FakeLlmClient(
        {
            _FMT: "The average grade in CS101 in 2024-Fall is 78.8.",
            "average grade": sql,
        }
    )
    result = test_graph(llm).invoke(
        {"question": "What is the average grade in CS101 in 2024-Fall?"}
    )
    assert result["terminal_reason"] == "ok"
    rows = result["rows"]
    assert rows is not None
    avg = list(rows[0].values())[0]
    assert abs(avg - 78.8) < 0.01


# ---------------------------------------------------------------------------
# 4. Three-table join: top student by average grade
# ---------------------------------------------------------------------------


def test_top_student_by_avg(test_graph):
    sql = (
        "SELECT s.name, AVG(e.grade) AS avg_grade "
        "FROM students s "
        "JOIN enrollments e ON s.id = e.student_id "
        "GROUP BY s.id ORDER BY avg_grade DESC LIMIT 1"
    )
    llm = FakeLlmClient(
        {
            _FMT: "Olivia Brown has the highest average grade at 91.5.",
            "highest average": sql,
        }
    )
    result = test_graph(llm).invoke({"question": "Which student has the highest average grade?"})
    assert result["terminal_reason"] == "ok"
    rows = result["rows"]
    assert rows is not None
    assert rows[0]["name"] == "Olivia Brown"
    assert "Olivia" in result["answer"]


# ---------------------------------------------------------------------------
# 5. Semester filter: courses offered in Spring 2025
# ---------------------------------------------------------------------------


def test_spring_2025_courses(test_graph):
    sql = (
        "SELECT DISTINCT c.title "
        "FROM courses c "
        "JOIN course_offerings co ON c.id = co.course_id "
        "WHERE co.semester = '2025-Spring' "
        "ORDER BY c.title"
    )
    llm = FakeLlmClient(
        {
            _FMT: "Two courses were offered in 2025-Spring: CS101 and CS301.",
            "2025-Spring": sql,
        }
    )
    result = test_graph(llm).invoke({"question": "Which courses were offered in 2025-Spring?"})
    assert result["terminal_reason"] == "ok"
    rows = result["rows"]
    assert rows is not None
    titles = [r["title"] for r in rows]
    assert any("CS101" in t for t in titles)
    assert any("CS301" in t for t in titles)


# ---------------------------------------------------------------------------
# 6. LEFT JOIN edge case: teacher with no offerings
# ---------------------------------------------------------------------------


def test_teacher_with_no_offerings(test_graph):
    sql = (
        "SELECT t.name "
        "FROM teachers t "
        "LEFT JOIN course_offerings co ON t.id = co.teacher_id "
        "WHERE co.id IS NULL"
    )
    llm = FakeLlmClient(
        {
            _FMT: "Dr. Carol Diaz has no course offerings.",
            "no course offerings": sql,
        }
    )
    result = test_graph(llm).invoke({"question": "Which teacher has no course offerings?"})
    assert result["terminal_reason"] == "ok"
    rows = result["rows"]
    assert rows is not None and len(rows) == 1
    assert rows[0]["name"] == "Dr. Carol Diaz"


# ---------------------------------------------------------------------------
# 7. NULL handling: count ungraded enrollments
# ---------------------------------------------------------------------------


def test_null_grade_count(test_graph):
    sql = "SELECT COUNT(*) AS ungraded FROM enrollments WHERE grade IS NULL"
    llm = FakeLlmClient(
        {
            _FMT: "There is 1 ungraded enrollment.",
            "no grade": sql,
        }
    )
    result = test_graph(llm).invoke({"question": "How many enrollments have no grade yet?"})
    assert result["terminal_reason"] == "ok"
    rows = result["rows"]
    assert rows is not None
    assert rows[0]["ungraded"] == 1


# ---------------------------------------------------------------------------
# 8. Aggregation with GROUP BY: average grade per offering
# ---------------------------------------------------------------------------


def test_aggregation_group_by(test_graph):
    sql = (
        "SELECT co.semester, AVG(e.grade) AS avg_grade "
        "FROM enrollments e "
        "JOIN course_offerings co ON e.offering_id = co.id "
        "GROUP BY co.semester ORDER BY co.semester"
    )
    llm = FakeLlmClient(
        {
            _FMT: "Average grades: 2024-Fall ~78, 2025-Spring ~77.",
            "semester": sql,
        }
    )
    result = test_graph(llm).invoke({"question": "What is the average grade per semester?"})
    assert result["terminal_reason"] == "ok"
    rows = result["rows"]
    assert rows is not None and len(rows) == 2
    semesters = {r["semester"] for r in rows}
    assert {"2024-Fall", "2025-Spring"} == semesters


# ---------------------------------------------------------------------------
# 9. Empty result: query that returns no rows
# ---------------------------------------------------------------------------


def test_empty_result_returns_canned_message(test_graph):
    sql = "SELECT * FROM students WHERE enrollment_year = 1800"
    llm = FakeLlmClient(
        {
            # No 'Query results' key — if LLM were called it would raise
            "1800": sql,
        }
    )
    result = test_graph(llm).invoke({"question": "Students enrolled in 1800?"})
    assert result["terminal_reason"] == "ok"
    assert result["rows"] == []
    assert "No matching records" in result["answer"]
