"""Integration tests — safety: non-SELECT rejection."""

from university_qa.adapters.fake_llm import FakeLlmClient


def test_drop_table_rejected(test_graph):
    """DROP TABLE terminates immediately with rejected_non_select, no execution."""
    llm = FakeLlmClient({"delete": "DROP TABLE students"})
    result = test_graph(llm).invoke({"question": "delete all students"})

    assert result["terminal_reason"] == "rejected_non_select"
    assert result["attempts"] == 1  # no retry
    assert result["rows"] is None  # execution never ran


def test_insert_rejected(test_graph):
    llm = FakeLlmClient({"add": "INSERT INTO students (name) VALUES ('Eve')"})
    result = test_graph(llm).invoke({"question": "add a new student named Eve"})

    assert result["terminal_reason"] == "rejected_non_select"
    assert result["rows"] is None


def test_update_rejected(test_graph):
    llm = FakeLlmClient({"update": "UPDATE students SET name='X' WHERE id=1"})
    result = test_graph(llm).invoke({"question": "update student name"})

    assert result["terminal_reason"] == "rejected_non_select"
    assert result["rows"] is None


def test_delete_rejected(test_graph):
    llm = FakeLlmClient({"remove": "DELETE FROM students WHERE id=1"})
    result = test_graph(llm).invoke({"question": "remove student 1"})

    assert result["terminal_reason"] == "rejected_non_select"
    assert result["rows"] is None


def test_non_select_does_not_retry(test_graph):
    """Non-SELECT must never loop back to generate_sql (attempts stays at 1)."""
    call_count = [0]

    class _CountingLlm(FakeLlmClient):
        def complete(self, system: str, user: str) -> str:
            if "Query results" not in user:
                call_count[0] += 1
            return "DROP TABLE students"

    result = test_graph(_CountingLlm({})).invoke({"question": "destroy everything"})

    assert result["terminal_reason"] == "rejected_non_select"
    assert call_count[0] == 1  # generate_sql called exactly once


def test_non_select_answer_is_fixed_refusal(test_graph):
    """The refusal message must not be LLM-generated (it's a fixed string)."""
    llm = FakeLlmClient({"drop": "DROP TABLE enrollments"})
    result = test_graph(llm).invoke({"question": "drop enrollments"})

    assert result["answer"] is not None
    # Fixed refusal references SELECT
    assert "SELECT" in result["answer"]


def test_attach_rejected(test_graph):
    llm = FakeLlmClient({"attach": 'ATTACH DATABASE "/tmp/x.db" AS x'})
    result = test_graph(llm).invoke({"question": "attach a database"})
    assert result["terminal_reason"] == "rejected_non_select"
    assert result["rows"] is None


def test_pragma_rejected(test_graph):
    llm = FakeLlmClient({"journal": "PRAGMA journal_mode=WAL"})
    result = test_graph(llm).invoke({"question": "change journal mode"})
    assert result["terminal_reason"] == "rejected_non_select"
    assert result["rows"] is None
