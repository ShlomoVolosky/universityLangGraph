"""Integration tests — retry behaviour."""

from university_qa.adapters.fake_llm import FakeLlmClient

_FMT = "Query results"


class _SequenceLlm(FakeLlmClient):
    """Returns responses in order per call index, ignoring pattern matching."""

    def __init__(self, sequence: list[str]) -> None:
        super().__init__({})
        self._seq = sequence
        self._idx = 0

    def complete(self, system: str, user: str) -> str:
        if _FMT in user:
            return "There are 5 students."
        resp = self._seq[min(self._idx, len(self._seq) - 1)]
        self._idx += 1
        return resp


def test_retry_bad_sql_then_good(test_graph):
    """FakeLlm returns bad SQL first, valid SQL second; assert attempts==2."""
    llm = _SequenceLlm(
        [
            "SELECT * FROM nonexistent_table",  # attempt 1: execution error
            "SELECT COUNT(*) AS cnt FROM students",  # attempt 2: succeeds
        ]
    )
    result = test_graph(llm).invoke({"question": "How many students?"})

    assert result["terminal_reason"] == "ok"
    assert result["attempts"] == 2
    assert len(result["prior_attempts"]) == 1
    assert result["rows"] is not None
    assert result["rows"][0]["cnt"] == 5


def test_retry_records_prior_attempt_sql_and_error(test_graph):
    """The (sql, error) from attempt 1 must appear in prior_attempts."""
    bad_sql = "SELECT * FROM no_such_table"
    llm = _SequenceLlm(
        [
            bad_sql,
            "SELECT COUNT(*) AS cnt FROM students",
        ]
    )
    result = test_graph(llm).invoke({"question": "How many students?"})

    assert len(result["prior_attempts"]) == 1
    recorded_sql, recorded_err = result["prior_attempts"][0]
    assert recorded_sql == bad_sql
    assert len(recorded_err) > 0  # error message non-empty


def test_retry_validation_failure_then_success(test_graph):
    """Validation failure (bad syntax) also triggers retry and records prior_attempts."""
    llm = _SequenceLlm(
        [
            "SELEKT * FORM students",  # attempt 1: parse/validation fail
            "SELECT COUNT(*) AS cnt FROM students",  # attempt 2: succeeds
        ]
    )
    result = test_graph(llm).invoke({"question": "How many students?"})

    assert result["terminal_reason"] == "ok"
    assert result["attempts"] == 2
    assert len(result["prior_attempts"]) == 1


def test_exhausted_retries_sets_terminal_reason(test_graph):
    """After max_attempts failures, terminal_reason='exhausted_retries'."""
    llm = _SequenceLlm(
        [
            "SELECT * FROM no_such_a",
            "SELECT * FROM no_such_b",
            "SELECT * FROM no_such_c",
        ]
    )
    result = test_graph(llm).invoke({"question": "How many students?", "max_attempts": 3})

    assert result["terminal_reason"] == "exhausted_retries"
    assert result["attempts"] == 3
    assert result["answer"] is not None
    assert "couldn't" in result["answer"].lower() or "could not" in result["answer"].lower()


def test_exhausted_retries_answer_mentions_attempt_count(test_graph):
    """Exhausted-retries answer references the attempt count."""
    llm = _SequenceLlm(["SELECT * FROM x", "SELECT * FROM y", "SELECT * FROM z"])
    result = test_graph(llm).invoke({"question": "test?", "max_attempts": 3})

    assert result["terminal_reason"] == "exhausted_retries"
    assert "3" in result["answer"]
