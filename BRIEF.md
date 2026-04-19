# University QA Agent — Implementation Brief for Claude Code

## 0. How to use this document

You are implementing a complete project from scratch based on this brief. Treat it as a binding specification: every constraint marked **MUST** is non-negotiable, every **SHOULD** is a strong default you may deviate from only with a one-line justification in code comments, and every **MAY** is a free choice.

Work in the phases listed in section 16, in order. At the end of each phase, the repo MUST be in a runnable, testable state — no broken imports, no skipped tests, no TODOs in the critical path. Commit at the end of each phase with a clear message.

If any instruction conflicts with another, the earlier section wins. If you encounter a design decision not covered here, prefer the option that (a) keeps the agent core independent of infrastructure, (b) is easiest to test with a fake, (c) is easiest to explain in an interview.

---

## 1. Mission

Build a question-answering system over a university database. Users ask natural-language questions ("What's the average grade in CS101 in 2025-Fall?"); the system generates SQL, runs it on a relational database, and returns a human-readable answer. The system MUST support aggregations, multi-table joins, filtering, and multi-step reasoning including retry on failure.

The three evaluation dimensions — stated explicitly so you can trade off correctly — are:

1. **Correctness** — the system answers correctly, including on complex queries.
2. **Explainability** — every run is traceable end-to-end; tests are deterministic; code is cleanly separated by responsibility.
3. **Portability** — the core agent is database-agnostic by construction. Swapping SQLite for Postgres changes adapters only, never agent code.

When choices trade off, prefer explainability over cleverness and portability over local convenience.

---

## 2. Architectural principles (MUST)

**Hexagonal / ports-and-adapters.** The agent core (LangGraph app, nodes, prompts, state) is the hexagon interior. It depends only on **port** interfaces, never on concrete infrastructure. Concrete infrastructure lives in **adapter** modules that implement those ports. A single **composition root** (`composition.py`) is the only file that imports both ports and adapters and wires them together.

**Dependency rule.** Imports flow inward only: `adapters` → `ports` ← `agent`. The `agent` package MUST NOT import anything from `adapters`. The `ports` package MUST NOT import anything from `adapters` or `agent`. Enforce this with an import-linter config or a test that inspects module ASTs — pick one, but enforce it mechanically, not by convention.

**Domain purity.** The `domain` package (Pydantic models, value objects) has zero dependencies on LangGraph, LangChain, database libraries, or HTTP clients. It MUST be importable in a context with only `pydantic` installed.

**Composition root pattern.** `composition.py` is the *only* place where adapter classes are named. Everything else depends on ports via constructor injection. This is what makes the "swap the database" demo a one-file change.

**Why this and not layered MVC?** Layered architecture encodes top-to-bottom dependencies, which tangles agent logic with persistence concerns. Hexagonal inverts control: the core defines interfaces, adapters implement them. That is the concrete meaning of the brief's "database-agnostic" requirement — not a convention, a compile-time (import-time) property.

---

## 3. Technology stack (MUST use exactly these unless noted)

- **Python 3.11+**. Use modern type hints (`list[str]`, `X | None`), no `typing.List` / `Optional`.
- **Pydantic v2** for all state, config, and boundary types. Runtime validation at every boundary is non-negotiable.
- **LangGraph** for the agent. The state graph is the control flow; do not hand-roll a sequencer.
- **LangChain core** only for LLM client abstractions if convenient — keep the surface area small; your own `LlmClient` port is what the agent depends on.
- **LangSmith** for production-path tracing. Wrap behind a `Tracer` port so tests can use a `NoopTracer`.
- **SQLite** (stdlib `sqlite3`) as the default adapter. Postgres adapter is a stretch goal.
- **sqlglot** for SQL AST validation and dialect awareness. Regex validation is forbidden.
- **pytest** + **pytest-asyncio** for tests. **hypothesis** MAY be used for property tests on the validator.
- **uv** or **pip** + `pyproject.toml` for dependency management. No `requirements.txt` as the source of truth.
- **ruff** for linting and formatting. **mypy** in strict mode for the `domain`, `ports`, and `agent` packages (adapters MAY relax this where third-party types are missing).

**Do NOT add:** ORMs (SQLAlchemy, etc.), web frameworks (FastAPI, Flask), ORMs for config (dynaconf), or anything else not on this list. A CLI is the only interface. If you think you need something here, stop and note it in the README's "future work" section instead.

**LLM provider:** Use Anthropic's API (`anthropic` Python SDK) by default. The `LlmClient` port MUST be abstract enough that an OpenAI adapter is a half-hour swap. Read the API key from `ANTHROPIC_API_KEY`.

---

## 4. Project structure (MUST match exactly)

```
university-qa/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── Makefile                        # make test, make run, make lint, make seed
├── src/
│   └── university_qa/
│       ├── __init__.py
│       ├── domain/                 # pure, zero infra dependencies
│       │   ├── __init__.py
│       │   ├── state.py            # AgentState Pydantic model
│       │   └── types.py            # QueryResult, Row, SchemaDescription, etc.
│       ├── ports/                  # abstract interfaces only
│       │   ├── __init__.py
│       │   ├── schema_provider.py
│       │   ├── sql_executor.py
│       │   ├── llm_client.py
│       │   └── tracer.py
│       ├── adapters/               # concrete implementations
│       │   ├── __init__.py
│       │   ├── sqlite_schema.py
│       │   ├── sqlite_executor.py
│       │   ├── anthropic_llm.py
│       │   ├── langsmith_tracer.py
│       │   ├── noop_tracer.py
│       │   └── fake_llm.py         # test-only; lives here so test code doesn't reach into prod paths
│       ├── agent/                  # LangGraph app; depends on ports only
│       │   ├── __init__.py
│       │   ├── graph.py            # build_graph()
│       │   ├── nodes.py            # one function per node
│       │   ├── prompts.py          # prompt templates, no f-strings with data
│       │   ├── validator.py        # sqlglot-based SQL validation
│       │   └── router.py           # conditional edge logic
│       ├── composition.py          # THE ONLY place adapters are named
│       ├── config.py               # pydantic Settings from env
│       └── cli.py                  # entry point: `python -m university_qa.cli`
├── db/
│   ├── schema.sql
│   └── seed.sql
├── scripts/
│   └── init_db.py                  # creates sqlite file, runs schema + seed
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # shared fixtures: in-memory DB, fake LLM, noop tracer
│   ├── unit/
│   │   ├── test_validator.py
│   │   ├── test_sqlite_schema.py
│   │   ├── test_sqlite_executor.py
│   │   └── test_architecture.py    # enforces the dependency rule
│   ├── integration/
│   │   ├── test_graph_happy_path.py
│   │   ├── test_graph_retry.py
│   │   └── test_graph_safety.py
│   └── e2e/
│       └── test_real_llm.py        # marked @pytest.mark.slow, skipped by default
└── docs/
    ├── architecture.md
    ├── design_decisions.md
    ├── production_checklist.md
    ├── example_queries.md
    └── traces/                     # exported LangSmith run links + screenshots
        └── README.md
```

---

## 5. Domain and ports (MUST implement these exact signatures)

### 5.1 `domain/state.py`

```python
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    # Input
    question: str

    # Schema context
    schema_snippet: str | None = None

    # SQL pipeline
    generated_sql: str | None = None
    validation_errors: list[str] = Field(default_factory=list)

    # Execution
    rows: list[dict] | None = None
    execution_error: str | None = None

    # Control
    attempts: int = 0
    max_attempts: int = 3

    # History for retry prompts — list of (sql, error) tuples from prior attempts
    prior_attempts: list[tuple[str, str]] = Field(default_factory=list)

    # Output
    answer: str | None = None

    # Terminal reason, for debugging — one of: "ok", "validation_failed",
    # "execution_failed", "exhausted_retries", "rejected_non_select"
    terminal_reason: str | None = None
```

The state MUST be a Pydantic model, not a `TypedDict`. Runtime validation at node boundaries is the whole point.

### 5.2 `domain/types.py`

Define `QueryResult` (`list[dict[str, Any]]` with a descriptive alias), `Row`, and a `SchemaDescription` value object that contains the schema text plus a list of known table names. Keep these lightweight — they exist so function signatures are self-documenting.

### 5.3 `ports/schema_provider.py`

```python
from abc import ABC, abstractmethod
from university_qa.domain.types import SchemaDescription

class SchemaProvider(ABC):
    @abstractmethod
    def describe(self) -> SchemaDescription: ...
```

`describe()` returns a textual schema summary suitable for injection into an LLM prompt. Format is implementation-defined but MUST include table names, columns with types, primary keys, and foreign-key relationships. See section 7 for the required format.

### 5.4 `ports/sql_executor.py`

```python
from abc import ABC, abstractmethod
from university_qa.domain.types import QueryResult

class SqlExecutor(ABC):
    @abstractmethod
    def run(self, sql: str) -> QueryResult: ...

    @property
    @abstractmethod
    def dialect(self) -> str: ...  # "sqlite", "postgres", etc.
```

Adapters MUST raise a typed `SqlExecutionError` (defined in `domain/types.py`) on failure, carrying both the original DB error and the SQL that was attempted. No raw `sqlite3.Error` should leak into the agent.

### 5.5 `ports/llm_client.py`

```python
from abc import ABC, abstractmethod

class LlmClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> str: ...
```

Keep the surface small. Two messages in, one string out. No streaming, no tool use (we don't need them and they complicate tracing).

### 5.6 `ports/tracer.py`

```python
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterator

class Tracer(ABC):
    @contextmanager
    @abstractmethod
    def span(self, name: str, **attributes: Any) -> Iterator[None]: ...

    @abstractmethod
    def event(self, name: str, **attributes: Any) -> None: ...
```

Two adapters required:

- `NoopTracer` — does nothing. Used in tests and when `LANGSMITH_TRACING` is off.
- `LangsmithTracer` — delegates to LangSmith. LangGraph auto-tracing covers node-level spans; this tracer wraps *custom* spans (schema fetch timing, validation results, retry counts) and forwards events to LangSmith via the SDK.

Do NOT make the agent call `Tracer` everywhere — LangGraph's built-in tracing is enough for node spans. Use `Tracer` for custom metrics inside nodes (e.g., "validator rejected SQL for reason X").

---

## 6. Adapters (MUST)

**`SqliteSchemaProvider`** introspects `sqlite_master` and `PRAGMA foreign_key_list` to build a `SchemaDescription`. Output format (for the LLM):

```
Dialect: sqlite

Tables:
  teachers(id INTEGER PK, name TEXT NOT NULL, department TEXT)
  students(id INTEGER PK, name TEXT NOT NULL, enrollment_year INTEGER)
  courses(id INTEGER PK, title TEXT NOT NULL, credits INTEGER NOT NULL)
  course_offerings(id INTEGER PK, course_id INTEGER, teacher_id INTEGER, semester TEXT NOT NULL)
  enrollments(id INTEGER PK, student_id INTEGER, offering_id INTEGER, grade REAL)

Relationships:
  course_offerings.course_id  -> courses.id
  course_offerings.teacher_id -> teachers.id
  enrollments.student_id      -> students.id
  enrollments.offering_id     -> course_offerings.id
```

Cache the result for the lifetime of the provider; schema doesn't change mid-run. Provide a `refresh()` method for tests.

**`SqliteExecutor`** opens the DB with `check_same_thread=False`, uses `Row` factory for dict results, and MUST connect in read-only mode (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`). Statement timeout via `sqlite3`'s `progress_handler` at ~5s. Raise `SqlExecutionError` on any failure with the offending SQL attached.

**`AnthropicLlmClient`** takes a model name (default `claude-sonnet-4-5` — confirm the current latest at build time) and an API key. Set `max_tokens=1024` for SQL generation, `max_tokens=512` for answer formatting. Temperature 0 for SQL generation, 0.2 for answer formatting. Retries on transient errors (5xx, rate limit) with exponential backoff, max 3 tries.

**`FakeLlmClient`** takes a dict `responses: dict[str, str]` mapping a substring-of-user-message to a response. On `complete()`, finds the first key that appears as a substring in the user message and returns its value; raises if none match. This is the workhorse of integration tests — it makes the graph deterministic.

**`LangsmithTracer`** is a thin wrapper over `langsmith.Client`. Only the custom spans and events we add go through it; LangGraph's auto-tracing does the rest.

**`NoopTracer`** is trivial — empty context manager, empty method.

---

## 7. Agent (LangGraph) specification

### 7.1 Graph shape

Five nodes, one conditional edge set:

```
START
  │
  ▼
load_schema ──► generate_sql ──► validate_sql
                    ▲                 │
                    │                 ▼
                    │          [validation ok?]
                    │           ├─ no  ──► route_after_validation ──┐
                    │           └─ yes ──► execute_sql              │
                    │                          │                    │
                    │                          ▼                    │
                    │                   [execution ok?]             │
                    │                    ├─ yes ──► format_answer ─► END
                    │                    └─ no  ──► route_after_execution
                    │                                    │
                    └────────────────────────────────────┘
                        (retry if attempts < max_attempts)
                                          │
                                          ▼
                                 [attempts exhausted or non-SELECT]
                                          │
                                          ▼
                                        END
```

### 7.2 Node contracts (all in `agent/nodes.py`)

Each node is a function `(state: AgentState, deps: Dependencies) -> dict`. The returned dict contains only the fields the node modifies; LangGraph merges it with existing state. Keep nodes small, pure-ish, and unit-testable.

- **`load_schema(state, deps)`** — calls `deps.schema_provider.describe()`, writes `schema_snippet`.
- **`generate_sql(state, deps)`** — calls `deps.llm.complete(system=GENERATE_SQL_SYSTEM, user=...)` with the question, schema, and any prior failed attempts from `state.prior_attempts`. Strips code fences from the response. Writes `generated_sql`, increments `attempts`.
- **`validate_sql(state, deps)`** — calls `validator.validate(state.generated_sql, dialect=deps.executor.dialect)`. Writes `validation_errors` (empty list on success).
- **`execute_sql(state, deps)`** — calls `deps.executor.run(state.generated_sql)`. On success, writes `rows`. On failure, writes `execution_error` and appends `(sql, error)` to `prior_attempts`.
- **`format_answer(state, deps)`** — calls the LLM with the question and rows, writes `answer` and `terminal_reason="ok"`. If `rows` is empty, bypass the LLM and return a templated "No matching records were found for that question."

### 7.3 Router (`agent/router.py`)

Two router functions, each returning a string that names the next node:

- `route_after_validation(state)` → `"execute_sql"` if `not state.validation_errors`, else `"retry_or_fail"`.
- `route_after_execution(state)` → `"format_answer"` if `state.execution_error is None`, else `"retry_or_fail"`.

The `"retry_or_fail"` logical branch is implemented by a tiny gate node that checks `state.attempts < state.max_attempts` and either routes back to `generate_sql` or sets `terminal_reason` and ends. Keep this logic in `router.py` — do not pollute nodes with control flow.

### 7.4 Non-SELECT hard stop

If the validator reports that the statement is not a `SELECT` (or is a `SELECT` containing `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ATTACH`/`PRAGMA`), set `terminal_reason="rejected_non_select"` and route directly to END with a fixed refusal message — do NOT retry. A retry with the error message in context could be prompt-injection amplification.

### 7.5 Validator (`agent/validator.py`)

Use `sqlglot.parse_one(sql, dialect=dialect)`. Reject if:

- parse fails (syntax error);
- the root node is not a `SELECT`;
- any descendant is an `Insert`, `Update`, `Delete`, `Drop`, `Alter`, `Create`, `Attach`, `Pragma`, or `Command`;
- any function call is in a denylist (at minimum: `load_extension`, `readfile`, `writefile`).

Return a dataclass `ValidationResult(ok: bool, errors: list[str], is_non_select: bool)`. The `is_non_select` flag is what the router uses to skip retries.

Unit-test this thoroughly — a dozen cases minimum. This is a security boundary.

---

## 8. Prompts (`agent/prompts.py`)

Prompts are Python constants at module level. No inline string-building in nodes. Each prompt has a `{schema}`, `{question}`, `{prior_attempts}` etc. slot and is filled via `.format(...)` at call time.

**`GENERATE_SQL_SYSTEM`** sets the role, lists hard constraints (SELECT only, target dialect, no DDL, prefer explicit JOINs, use table aliases, return ONLY the SQL with no prose or markdown fences), and embeds the schema. Keep under 400 tokens.

**`GENERATE_SQL_USER`** contains the question, and — if `prior_attempts` is non-empty — a block listing each prior SQL and its error, with the instruction "Your previous attempts failed. Learn from the errors and generate a corrected query."

**`FORMAT_ANSWER_SYSTEM`** instructs the model to write a concise, human-readable answer grounded in the rows, citing exact numbers from the rows, refusing to invent values not present, and keeping to 1–3 sentences.

**`FORMAT_ANSWER_USER`** contains the original question and the rows (JSON-serialized, truncated to the first 50 rows with a note if truncated).

Every prompt MUST be importable and testable standalone. No environment access, no I/O at import time.

---

## 9. Database

### 9.1 Schema (`db/schema.sql`)

```sql
CREATE TABLE teachers (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    department TEXT
);

CREATE TABLE students (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    enrollment_year INTEGER
);

CREATE TABLE courses (
    id      INTEGER PRIMARY KEY,
    title   TEXT NOT NULL,
    credits INTEGER NOT NULL
);

CREATE TABLE course_offerings (
    id         INTEGER PRIMARY KEY,
    course_id  INTEGER NOT NULL REFERENCES courses(id),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    semester   TEXT    NOT NULL,
    UNIQUE (course_id, teacher_id, semester)
);

CREATE TABLE enrollments (
    id          INTEGER PRIMARY KEY,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    offering_id INTEGER NOT NULL REFERENCES course_offerings(id),
    grade       REAL,
    UNIQUE (student_id, offering_id)
);

CREATE INDEX idx_enrollments_offering ON enrollments(offering_id);
CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE INDEX idx_offerings_semester ON course_offerings(semester);
```

### 9.2 Seed (`db/seed.sql`)

Include at minimum:

- 3 teachers across 2 departments
- 15 students across 3 enrollment years
- 5 courses with varied credit values
- 12 course offerings spanning 2 semesters ("2024-Fall", "2025-Spring"), with at least one course offered in both semesters by different teachers
- 60+ enrollments with grades distributed roughly realistically (mean ~75, stddev ~12, some nulls for ungraded)

Include deliberately tricky data for test coverage:

- one student enrolled in the same course across two semesters
- one enrollment with `grade = NULL` (not yet graded)
- one teacher with no course offerings (the query `teachers LEFT JOIN offerings` must handle them)
- one course with no offerings in the current data

### 9.3 Init script (`scripts/init_db.py`)

Creates `db/university.db` from `schema.sql` + `seed.sql`. Idempotent: if the file exists, refuse unless `--force` is passed. Used by `make seed`.

---

## 10. Tracing

### 10.1 LangSmith configuration

Environment variables:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=university-qa-dev
```

LangGraph picks these up automatically and traces every node invocation with inputs, outputs, and latency. This alone satisfies the brief's "clearly present full run traces" requirement.

### 10.2 Custom spans (inside nodes, via the `Tracer` port)

Add explicit spans for:

- `schema.fetch` — dimensions: table_count, total_column_count
- `sql.validate` — dimensions: ok (bool), is_non_select (bool), error_count
- `sql.execute` — dimensions: row_count, duration_ms, succeeded (bool)
- `answer.format` — dimensions: input_row_count, truncated (bool)

Custom events:

- `retry` with attempt number and last error — fires whenever we loop back to `generate_sql`
- `terminal` with `terminal_reason` — fires once per run at END

### 10.3 Trace exports

`docs/traces/README.md` MUST contain at least three real LangSmith run links (or screenshots if links aren't shareable): one happy path with a 3-table join, one retry scenario, one rejected-non-SELECT scenario. These are interview demo material — they MUST exist at phase-10 completion.

---

## 11. Error handling (MUST)

Categorize failures explicitly, document each in `docs/design_decisions.md`:

1. **Parse / validation failure** — loop back with the error in the prompt. Capped at `max_attempts=3`.
2. **Non-SELECT statement** — no retry. Terminal state with a fixed refusal. Logged as a security event.
3. **Execution error** (bad column name, type mismatch, etc.) — loop back with the error. Same cap.
4. **Empty result** — not an error. Bypass the formatter LLM, return a canned message. Don't let the LLM hallucinate numbers into a 0-row answer.
5. **Retries exhausted** — terminal state. Return an honest "I couldn't produce a valid query for this question after N tries." Include `terminal_reason="exhausted_retries"` and the last error.
6. **Ambiguous question** — out of scope for v1. Document as future work: a pre-generation clarification node.

Every terminal state MUST set `terminal_reason`. Every retry MUST append to `prior_attempts` so the next prompt has the full history. The number of retries MUST be configurable via `AgentState.max_attempts` (default 3).

---

## 12. Testing strategy (MUST)

### 12.1 Three tiers

**Unit tests (`tests/unit/`).** Fast, no network, no LLM. Test:

- `validator.py` exhaustively: accepts, rejects, edge cases (CTEs, subqueries, window functions should be accepted if SELECT-rooted).
- `sqlite_schema.py`: against an in-memory DB with a known schema, assert `describe()` output matches expected format byte-for-byte.
- `sqlite_executor.py`: happy path, syntax error, read-only enforcement (attempt an INSERT → raises).
- `test_architecture.py`: a test that imports each of `domain`, `ports`, `agent` and asserts (via `importlib` inspection or AST) that they do not transitively import anything under `adapters`. This is the mechanical enforcement of the dependency rule.

**Integration tests (`tests/integration/`).** Test the full graph against an in-memory SQLite and a `FakeLlmClient`. Deterministic. Test:

- `test_graph_happy_path.py`: question → expected SQL → expected rows → expected answer substring. Cover single-table, join, aggregation, and multi-semester filter cases — at least 6 scenarios.
- `test_graph_retry.py`: FakeLlm returns bad SQL first, good SQL second. Assert `attempts == 2`, `prior_attempts` length 1, final answer correct.
- `test_graph_safety.py`: FakeLlm returns a DROP TABLE. Assert the graph terminates with `terminal_reason="rejected_non_select"`, no execution attempted, no retry.

**E2E tests (`tests/e2e/`).** Real Anthropic LLM, real SQLite. Marked `@pytest.mark.slow`, excluded from default `pytest` run. CI runs them nightly. 5–8 natural-language questions, asserting on semantic content (`"3" in answer` rather than exact string match). Skip if `ANTHROPIC_API_KEY` is not set.

### 12.2 Fixtures (`tests/conftest.py`)

- `in_memory_db`: fresh `sqlite3.connect(":memory:")` seeded from `schema.sql` + a compact test-seed (subset of production seed, deterministic IDs).
- `fake_llm`: factory that takes a `{pattern: response}` dict and returns a `FakeLlmClient`.
- `noop_tracer`: instance of `NoopTracer`.
- `test_graph`: factory that wires the above into a `Dependencies` bundle and builds the graph.

### 12.3 Coverage and CI

- `make test` runs unit + integration, must complete in under 10 seconds.
- `make test-all` includes e2e.
- Target coverage: 90%+ on `domain`, `ports`, `agent`. Adapters: 80%+.
- CI (GitHub Actions) runs `make lint && make test` on push. No e2e in CI unless manually dispatched.

---

## 13. CLI (`cli.py`)

Minimal. `python -m university_qa.cli "what's the average grade in CS101?"` prints the answer. Flags:

- `--db PATH` — override default `db/university.db`.
- `--model NAME` — override default model.
- `--trace` — print the LangSmith run URL on completion.
- `--debug` — print full final state (all fields) after run, for debugging.

Use `argparse` from stdlib, not click/typer. Keep it under 80 lines.

---

## 14. Configuration (`config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-5"
    db_path: str = "db/university.db"
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "university-qa-dev"
    max_attempts: int = 3

    class Config:
        env_file = ".env"
```

`.env.example` MUST list every variable with a placeholder. Secrets are never committed. `.gitignore` MUST include `.env` and `db/*.db`.

---

## 15. Documentation

**`README.md`** — quickstart (install, seed, run), example invocation, one paragraph of architectural overview, link to `docs/architecture.md`.

**`docs/architecture.md`** — the hexagonal diagram (ASCII or mermaid), a paragraph on each port and its adapters, the "how to swap the database" walkthrough. Include the full graph diagram from section 7.1.

**`docs/design_decisions.md`** — a numbered list of every non-obvious choice with a 2–3 sentence rationale. Minimum entries:

1. Why hexagonal (not layered).
2. Why Pydantic state (not TypedDict).
3. Why LangGraph (not a plain chain).
4. Why `course_offerings` is its own table.
5. Why sqlglot (not regex) for validation.
6. Why FakeLlmClient (not mocking libraries).
7. Why the non-SELECT path does not retry.
8. Why empty results bypass the formatter LLM.
9. Why read-only SQLite connection (defense in depth).
10. How DB-agnosticism is structurally enforced, not just promised.

**`docs/production_checklist.md`** — the production considerations from section 8 of the brief, organized as security / reliability / scalability / observability / deployment / cost / data governance. Not aspirational — concrete: "use a read-only Postgres user for `SqlExecutor`; rotate credentials with X; rate-limit at Y RPS per user at the gateway."

**`docs/example_queries.md`** — 10+ example questions with their generated SQL and final answer, organized by complexity (single-table, join, aggregation, multi-step, edge-case). This is interview demo material.

**`docs/traces/README.md`** — see section 10.3.

---

## 16. Execution phases (MUST follow in order)

Each phase ends in a runnable, test-passing commit.

**Phase 1 — skeleton.** Create the directory tree, `pyproject.toml`, `.gitignore`, `README.md`, `Makefile`. `pytest` runs and finds zero tests. `ruff check .` passes.

**Phase 2 — domain + ports.** Implement `domain/state.py`, `domain/types.py`, and all four port interfaces. No adapters yet. `mypy --strict src/university_qa/domain src/university_qa/ports` passes.

**Phase 3 — database layer.** Write `db/schema.sql`, `db/seed.sql`, `scripts/init_db.py`. Running `make seed` produces a populated SQLite file. Implement `SqliteSchemaProvider` and `SqliteExecutor`. Write their unit tests. `make test` passes.

**Phase 4 — validator.** Implement `agent/validator.py` using sqlglot. Write exhaustive unit tests (minimum 12 cases). Include the architecture test in `tests/unit/test_architecture.py`.

**Phase 5 — fake LLM and noop tracer.** Implement `FakeLlmClient` and `NoopTracer`. These unblock integration testing before real-LLM code exists.

**Phase 6 — prompts and graph.** Write `agent/prompts.py`, `agent/nodes.py`, `agent/router.py`, `agent/graph.py`. Wire them together using only ports — no `composition.py` yet. Confirm by trying to import `adapters` from `agent/*.py` files and verifying it fails your architecture test.

**Phase 7 — composition and CLI.** Implement `composition.py` and `cli.py`. Implement `AnthropicLlmClient`. `python -m university_qa.cli "how many students are there?"` runs end-to-end against the real LLM and prints an answer.

**Phase 8 — integration tests.** Write `test_graph_happy_path.py`, `test_graph_retry.py`, `test_graph_safety.py` using the fake LLM. All pass deterministically.

**Phase 9 — tracing.** Implement `LangsmithTracer`. Add custom spans inside nodes per section 10.2. Run a handful of real queries with tracing on; confirm runs appear in LangSmith.

**Phase 10 — documentation and trace exports.** Write all docs per section 15. Run 3+ demo queries with tracing, capture run URLs/screenshots into `docs/traces/`. Populate `docs/example_queries.md` with real outputs.

**Phase 11 — e2e tests.** Write `tests/e2e/test_real_llm.py`. Mark slow. Confirm they pass when run manually.

**Phase 12 — polish.** Full `ruff`, `mypy`, coverage check. README final pass. Rehearse the "swap to Postgres" explanation and write it up (you don't need to implement the Postgres adapter, but document exactly what it would entail and confirm by inspection that only `composition.py` would change).

---

## 17. Definition of done

- [ ] All 12 phases complete and committed.
- [ ] `make test` green, under 10 seconds.
- [ ] `make lint` green (`ruff` + `mypy --strict` on core packages).
- [ ] The CLI answers at least the 10 example questions in `docs/example_queries.md` correctly on a fresh DB.
- [ ] LangSmith traces exist for at least 3 runs and are linked in `docs/traces/README.md`.
- [ ] Architecture test in `tests/unit/test_architecture.py` passes and genuinely inspects imports (not a stub).
- [ ] `docs/design_decisions.md` has all 10 decisions with rationale.
- [ ] The README has a "Running the demo" section that works on a clean clone with only `ANTHROPIC_API_KEY` set.

---

## 18. Anti-requirements (do NOT do)

- Do NOT add a web framework, ORM, or message queue.
- Do NOT use `TypedDict` for state. Pydantic only.
- Do NOT use regex to validate SQL. sqlglot only.
- Do NOT hardcode the schema in any prompt, node, or adapter outside `SchemaProvider`.
- Do NOT let adapter types leak into agent code. If you find yourself importing `sqlite3` in `agent/`, stop.
- Do NOT catch-and-swallow exceptions in nodes. Let typed errors flow into state; let unexpected errors crash — the tracer will capture them.
- Do NOT write a retry loop with `while`. The LangGraph cycle IS the retry loop.
- Do NOT add features not in this brief. "Nice to have" goes in `docs/future_work.md`, not in the code.
- Do NOT skip the `test_architecture.py` test. It is the only mechanical guarantee of the hexagonal property.

---

## 19. Interview-readiness notes

The reviewer will ask you to justify every decision in this document. Your code, tests, and docs MUST make each justification easy to demonstrate. Concretely:

- "Why hexagonal?" → point at `test_architecture.py` and at `composition.py`.
- "Swap the database?" → point at the `SchemaProvider` / `SqlExecutor` ports and read out the single line of `composition.py` that would change.
- "Show me a retry." → run a specific question that you know triggers one, open the LangSmith trace, show the two `generate_sql` spans.
- "Show me a safety rejection." → run the canned DROP-TABLE demo question, show `terminal_reason="rejected_non_select"`.
- "What would production need?" → open `docs/production_checklist.md` and walk through it.

Every item on that list must be demonstrable with the artifacts in the repo. If you can't demo it, the feature isn't done.

---

*End of brief. Begin with Phase 1.*
