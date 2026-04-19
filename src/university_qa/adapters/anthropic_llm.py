import time

import anthropic

from university_qa.ports.llm_client import LlmClient

_SQL_MAX_TOKENS = 1024
_SQL_TEMPERATURE = 0.0
_FMT_MAX_TOKENS = 512
_FMT_TEMPERATURE = 0.2

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class AnthropicLlmClient(LlmClient):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        # Use tighter params for answer formatting; SQL generation needs more tokens.
        is_format = "Query results" in user
        max_tokens = _FMT_MAX_TOKENS if is_format else _SQL_MAX_TOKENS
        temperature = _FMT_TEMPERATURE if is_format else _SQL_TEMPERATURE

        last_exc: Exception = RuntimeError("no attempts made")
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return str(response.content[0].text)  # type: ignore[union-attr]
            except anthropic.RateLimitError as exc:
                last_exc = exc
            except anthropic.APIStatusError as exc:
                if exc.status_code not in _RETRYABLE_STATUS:
                    raise
                last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE * (2**attempt))
        raise last_exc
