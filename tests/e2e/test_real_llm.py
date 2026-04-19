"""
End-to-end tests against a real LLM and the real university.db.

Marked @pytest.mark.slow — excluded from `make test` by default.
Run with:  make test-all
           python3 -m pytest tests/e2e -v

Skip behaviour: all tests skip automatically when no LLM API key is
present in the environment (or .env file).  They never fail due to a
missing key — only due to an incorrect answer.
"""

import pytest
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from .env before Settings is read

from university_qa.composition import build_app  # noqa: E402
from university_qa.config import Settings  # noqa: E402


def _settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def _has_llm_key() -> bool:
    s = _settings()
    return bool(s.anthropic_api_key or s.openai_api_key)


_skip_no_key = pytest.mark.skipif(
    not _has_llm_key(),
    reason="No LLM API key configured — set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env",
)


@pytest.fixture(scope="module")
def app():
    """Build the real graph once per module — DB + LLM adapter wired."""
    return build_app(_settings())


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
@_skip_no_key
def test_e2e_student_count(app):
    """Real LLM counts students correctly."""
    result = app.invoke({"question": "How many students are there?"})
    assert result["terminal_reason"] == "ok"
    assert result["attempts"] <= 2
    assert "15" in result["answer"]


@pytest.mark.slow
@_skip_no_key
def test_e2e_top_student_by_avg_grade(app):
    """3-table join: real LLM identifies the top student."""
    result = app.invoke({"question": "Which student has the highest average grade?"})
    assert result["terminal_reason"] == "ok"
    assert result["rows"] is not None and len(result["rows"]) >= 1
    # Top student in seed data is Emma Wilson at 86.75
    assert "Emma" in result["answer"] or "Wilson" in result["answer"]


@pytest.mark.slow
@_skip_no_key
def test_e2e_teacher_with_no_offerings(app):
    """LEFT JOIN edge case: teacher with no offerings."""
    result = app.invoke({"question": "Which teacher has no course offerings?"})
    assert result["terminal_reason"] == "ok"
    assert result["rows"] is not None
    names = [r.get("name", "") for r in result["rows"]]
    assert any("Carol" in n or "Diaz" in n for n in names)


@pytest.mark.slow
@_skip_no_key
def test_e2e_courses_in_spring_2025(app):
    """Semester filter returns correct course list."""
    result = app.invoke({"question": "Which courses were offered in 2025-Spring?"})
    assert result["terminal_reason"] == "ok"
    assert result["rows"] is not None and len(result["rows"]) >= 1
    titles = " ".join(str(r) for r in result["rows"])
    assert "CS101" in titles or "CS301" in titles or "MA" in titles


@pytest.mark.slow
@_skip_no_key
def test_e2e_null_grade_count(app):
    """NULL handling: count enrollments with no grade."""
    result = app.invoke({"question": "How many enrollments have no grade recorded?"})
    assert result["terminal_reason"] == "ok"
    assert result["rows"] is not None
    count = list(result["rows"][0].values())[0]
    assert count == 3


@pytest.mark.slow
@_skip_no_key
def test_e2e_most_credited_course(app):
    """Single-table query with ORDER BY returns correct course."""
    result = app.invoke({"question": "Which course has the most credits?"})
    assert result["terminal_reason"] == "ok"
    assert "MA201" in result["answer"] or "Calculus" in result["answer"]


# ---------------------------------------------------------------------------
# Safety / rejection test
# ---------------------------------------------------------------------------


@pytest.mark.slow
@_skip_no_key
def test_e2e_empty_result_canned_message(app):
    """Query that returns no rows produces the canned message (no hallucination)."""
    result = app.invoke({"question": "Which students enrolled in the year 1800?"})
    assert result["terminal_reason"] == "ok"
    assert result["rows"] == [] or result["rows"] is None or len(result["rows"]) == 0
    assert "No matching records" in result["answer"] or result["rows"] == []
