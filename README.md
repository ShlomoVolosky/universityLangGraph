# University QA Agent

A natural-language question-answering system over a university database, built with LangGraph and Anthropic's Claude.

## Quickstart

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Set your API key
cp .env.example .env
# edit .env and fill in ANTHROPIC_API_KEY

# 3. Seed the database
make seed

# 4. Ask a question
python -m university_qa.cli "Which student has the highest average grade?"
```

## Running the demo

```bash
# Single question
python -m university_qa.cli "How many students enrolled in 2024?"

# With full state debug output (shows generated SQL, rows, attempts)
python -m university_qa.cli "Which teacher has the most course offerings?" --debug

# With LangSmith run URL printed on completion (requires LANGSMITH_TRACING=true)
python -m university_qa.cli "What is the average grade per semester?" --trace
```

Only `ANTHROPIC_API_KEY` is required for a clean-clone run. All other settings have defaults.
See [`docs/example_queries.md`](docs/example_queries.md) for 10 example questions with real outputs.

## Architecture overview

The system follows a **hexagonal (ports-and-adapters)** architecture. The agent core — the LangGraph state machine, nodes, prompts, and router — depends only on abstract port interfaces. Concrete infrastructure (SQLite, Anthropic API, LangSmith) lives in adapter modules and is wired together in a single composition root (`composition.py`). Swapping the database requires changing exactly one file.

See [`docs/architecture.md`](docs/architecture.md) for the full diagram, port/adapter breakdown, and the "swap to Postgres" walkthrough.

## Running tests

```bash
make test       # unit + integration (fast, no LLM required, ~0.4 s)
make lint       # ruff check + ruff format --check + mypy --strict
```

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/architecture.md`](docs/architecture.md) | Hexagonal diagram, port/adapter table, graph flow, Postgres swap walkthrough |
| [`docs/design_decisions.md`](docs/design_decisions.md) | 10 non-obvious design choices with rationale |
| [`docs/production_checklist.md`](docs/production_checklist.md) | Security, reliability, scalability, observability, cost, data governance |
| [`docs/example_queries.md`](docs/example_queries.md) | 10 example questions with generated SQL and real answers |
| [`docs/traces/README.md`](docs/traces/README.md) | 3 real LangSmith run links (happy path, retry, rejected non-SELECT) |

## Future work

- Postgres adapter (only `composition.py` changes — see `docs/architecture.md`)
- Pre-generation clarification node for ambiguous questions
- Streaming answers for large result sets
- Rate limiting and per-user auth for multi-tenant deployment
