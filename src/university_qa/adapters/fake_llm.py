from university_qa.ports.llm_client import LlmClient


class FakeLlmClient(LlmClient):
    """Deterministic LLM for integration tests.

    Matches the first key from `responses` that appears as a substring of the
    user message and returns its value.  Raises if no key matches — that is an
    error in the test, not in the system under test.
    """

    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses

    def complete(self, system: str, user: str) -> str:
        for pattern, response in self._responses.items():
            if pattern in user:
                return response
        raise ValueError(
            f"FakeLlmClient: no pattern matched user message.\n"
            f"Patterns: {list(self._responses)}\n"
            f"User (first 200 chars): {user[:200]}"
        )
