# Design Decisions

Ten non-obvious choices, each with a 2–3 sentence rationale.

---

## 1. Why hexagonal architecture (not layered MVC)

Layered MVC encodes a top-to-bottom dependency: controller → service → repository. That tangles the agent's control flow with persistence concerns, making it impossible to test the agent without a real database. Hexagonal inverts the dependency — the agent core defines interfaces (ports) and infrastructure implements them — so the core is testable with a `FakeLlmClient` and an in-memory SQLite DB, with zero changes to production code.

## 2. Why Pydantic state (not TypedDict)

LangGraph supports both, but `TypedDict` is a structural hint with no runtime enforcement. Pydantic `BaseModel` validates every field on merge, catching type mismatches early (e.g., a node accidentally returning `rows={"count": 5}` instead of `rows=[{"count": 5}]`). It also makes default-factory fields (`prior_attempts: list[tuple[str, str]] = Field(default_factory=list)`) safe across concurrent invocations, since each state object is independent.

## 3. Why LangGraph (not a plain chain)

A plain chain is a linear sequence; this agent has conditional branching (retry vs. reject vs. succeed) and a loop (back to `generate_sql` on failure). Encoding that in a `chain` produces spaghetti callbacks or a hand-rolled state machine. LangGraph expresses the control flow as a declarative graph with typed edges, making the retry/reject logic visible and independently testable in `router.py`.

## 4. Why `course_offerings` is its own table

Courses are offered multiple times (different semesters, different teachers). Without a join table, recording "who taught CS101 in Fall 2024" requires either duplicating course data or a non-normal schema. `course_offerings` is the standard relational pattern for a many-to-many relationship between courses, teachers, and semesters; it also lets enrollments reference a specific offering (not just a course), which is required for per-semester grade tracking.

## 5. Why sqlglot (not regex) for SQL validation

Regex can catch `DROP TABLE` literally, but cannot handle `WITH cte AS (DROP TABLE ...)` or a `SELECT` containing an `INSERT` subquery. sqlglot parses the full AST, so we can walk every descendant node and reject forbidden types regardless of nesting depth. It also provides dialect-aware parsing (`sqlglot.parse_one(sql, dialect="sqlite")`), which is critical when we add a Postgres adapter.

## 6. Why FakeLlmClient (not mocking libraries)

`unittest.mock.patch` mocks are fragile: they break when the call site changes (e.g., argument order or keyword names) and they leak implementation details into the test. `FakeLlmClient` is a real implementation of the `LlmClient` port — it has no knowledge of call sites and is controlled entirely by a `{pattern: response}` dict. This lets integration tests run the full graph end-to-end without touching the network, and lets the pattern dict serve as explicit documentation of what the LLM is expected to return.

## 7. Why the non-SELECT path does not retry

If the LLM generated `DROP TABLE students`, feeding that error back into the prompt creates a retry with the dangerous SQL visible in context. An adversarial question could exploit this: craft a question that reliably elicits a `DROP TABLE`, then use the error message (which echoes the SQL) to probe the system. The fix is categorical: non-SELECT is a terminal state with a fixed refusal message — no loop, no LLM call, no echo of the original SQL in the answer.

## 8. Why empty results bypass the formatter LLM

An LLM asked to summarize zero rows has nothing to ground itself on and will hallucinate. The pattern is well-documented: models often invent plausible-sounding numbers when given empty inputs. The fix is structural: if `rows == []`, return a canned `"No matching records were found"` message without ever calling the formatter. This eliminates a whole class of hallucination for free.

## 9. Why read-only SQLite connection

The executor opens SQLite with `file:{path}?mode=ro&uri=true`. Even if the validator has a bug and passes a `DELETE` statement, the OS-level read-only flag on the connection will cause SQLite to reject it with an error. Defense in depth: the validator is the first line, the read-only connection is the second. Neither alone is sufficient; both together mean a bypass requires compromising two independent mechanisms.

## 10. How DB-agnosticism is structurally enforced, not just promised

`tests/unit/test_architecture.py` walks the AST of every module in `domain/`, `ports/`, and `agent/` and asserts that none of them import from `adapters`. It also asserts that `domain/` imports no infrastructure libraries (no `sqlite3`, `anthropic`, `langraph`, etc.). This test runs in CI on every commit. "Database-agnostic" is therefore a compile-time (import-time) property, not a convention: if an engineer accidentally writes `from university_qa.adapters.sqlite_executor import SqliteExecutor` inside a node, the test fails immediately.
