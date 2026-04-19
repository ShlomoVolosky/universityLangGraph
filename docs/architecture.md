# Architecture

## Hexagonal (ports-and-adapters) overview

```
                        ┌─────────────────────────────────────┐
                        │           Agent Core (hexagon)       │
                        │                                      │
  ┌──────────────┐      │  agent/graph.py  agent/nodes.py     │
  │  SQLite      │      │  agent/router.py agent/prompts.py   │
  │  Adapter     │─────▶│  agent/validator.py                 │
  └──────────────┘      │                                      │
                        │  domain/state.py  domain/types.py   │
  ┌──────────────┐      │                                      │
  │  Anthropic / │      │         ▲ port interfaces ▼         │
  │  OpenAI LLM  │─────▶│  SchemaProvider  SqlExecutor        │
  │  Adapter     │      │  LlmClient       Tracer             │
  └──────────────┘      │                                      │
                        └──────────────┬──────────────────────┘
  ┌──────────────┐                     │
  │  LangSmith   │◀────────────────────┘
  │  Tracer      │      composition.py (sole wiring point)
  └──────────────┘
```

Imports flow **inward only**: `adapters` → `ports` ← `agent`. The `agent` package
never imports from `adapters`. Enforced mechanically by `tests/unit/test_architecture.py`.

---

## Ports

| Port | File | Contract |
|------|------|----------|
| `SchemaProvider` | `ports/schema_provider.py` | `describe() -> SchemaDescription` |
| `SqlExecutor` | `ports/sql_executor.py` | `run(sql) -> list[Row]`, `dialect: str` |
| `LlmClient` | `ports/llm_client.py` | `complete(system, user) -> str` |
| `Tracer` | `ports/tracer.py` | `span(name, **attrs)` context manager, `event(name, **attrs)` |

---

## Adapters

| Adapter | Port | Notes |
|---------|------|-------|
| `SqliteSchemaProvider` | `SchemaProvider` | Introspects `sqlite_master` + `PRAGMA table_info/foreign_key_list`; caches; supports `refresh()` |
| `SqliteExecutor` | `SqlExecutor` | Read-only URI connection; `sqlite3.Row` factory for dict results; 5 s progress-handler timeout |
| `AnthropicLlmClient` | `LlmClient` | Exponential backoff on 429/5xx; detects SQL-gen vs format-answer call to set appropriate `max_tokens` |
| `OpenAiLlmClient` | `LlmClient` | Same structure; selected when `OPENAI_API_KEY` set and `ANTHROPIC_API_KEY` absent |
| `FakeLlmClient` | `LlmClient` | Substring-match dict; deterministic; used in all unit and integration tests |
| `LangsmithTracer` | `Tracer` | Custom sub-spans via `get_current_run_tree()`; EU endpoint configurable via `LANGSMITH_ENDPOINT` |
| `NoopTracer` | `Tracer` | No-op context manager and event; used when tracing is disabled |

---

## LangGraph state machine

```
START
  │
  ▼
load_schema ──► generate_sql ──► validate_sql
                    ▲                 │
                    │                 ▼
                    │          [validation ok?]
                    │           ├─ no, non-SELECT ──► reject_non_select ──► END
                    │           ├─ no, retryable  ──► retry_or_fail ─────┐
                    │           └─ yes ──► execute_sql                   │
                    │                          │                          │
                    │                          ▼                          │
                    │                   [execution ok?]                   │
                    │                    ├─ yes ──► format_answer ──► END │
                    │                    └─ no  ──► retry_or_fail         │
                    │                                    │                │
                    │                    ┌───────────────┘                │
                    │                    ▼                                 │
                    │             [attempts < max?]                        │
                    │              ├─ yes ──────────────────────────────── ┘
                    └──────────────┘
                              │
                              └─ no ──► END  (terminal_reason=exhausted_retries)
```

### Node contracts

Every node is `(state: AgentState, deps: Dependencies) -> dict`. LangGraph merges
the returned dict into state. Nodes never import from `adapters`.

| Node | Reads | Writes |
|------|-------|--------|
| `load_schema` | — | `schema_snippet` |
| `generate_sql` | `schema_snippet`, `prior_attempts`, `question` | `generated_sql`, `attempts+1` |
| `validate_sql` | `generated_sql` | `validation_errors` |
| `execute_sql` | `generated_sql` | `rows` or `execution_error`, `prior_attempts` |
| `format_answer` | `question`, `rows` | `answer`, `terminal_reason` |
| `retry_or_fail` | `attempts`, `max_attempts`, `validation_errors` | `prior_attempts`, `terminal_reason?`, `answer?` |
| `reject_non_select` | — | `terminal_reason`, `answer` |

---

## How to swap the database (Postgres example)

Only `composition.py` changes. Steps:

1. Install `psycopg2` (or `asyncpg`).
2. Write `adapters/postgres_executor.py` implementing `SqlExecutor` with `dialect = "postgres"`.
3. Write `adapters/postgres_schema.py` implementing `SchemaProvider` using `information_schema`.
4. In `composition.py`, replace:
   ```python
   conn = sqlite3.connect(...)
   deps = Dependencies(
       schema_provider=SqliteSchemaProvider(conn),
       executor=SqliteExecutor(conn),
       ...
   )
   ```
   with:
   ```python
   deps = Dependencies(
       schema_provider=PostgresSchemaProvider(dsn=settings.db_dsn),
       executor=PostgresExecutor(dsn=settings.db_dsn),
       ...
   )
   ```

No agent code, no prompt, no port, no test fixture changes. The architecture test
will still pass because `agent/` never imported `sqlite3` or any adapter type.
