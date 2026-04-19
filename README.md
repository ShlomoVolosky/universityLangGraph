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
python -m university_qa.cli "What's the average grade in CS101 in 2025-Spring?"
```

## Running the demo

```bash
# Single question
python -m university_qa.cli "How many students enrolled in 2024?"

# With full state debug output
python -m university_qa.cli "Which teacher has the most course offerings?" --debug

# With LangSmith run URL printed on completion
python -m university_qa.cli "What is the average grade per department?" --trace
```

## Architecture overview

The system follows a **hexagonal (ports-and-adapters)** architecture. The agent core — the LangGraph state machine, nodes, prompts, and router — depends only on abstract port interfaces. Concrete infrastructure (SQLite, Anthropic API, LangSmith) lives in adapter modules and is wired together in a single composition root (`composition.py`). Swapping the database requires changing exactly one line in `composition.py`.

See [`docs/architecture.md`](docs/architecture.md) for the full diagram and port/adapter breakdown.

## Running tests

```bash
make test       # unit + integration (fast, no LLM required)
make test-all   # includes e2e tests (requires ANTHROPIC_API_KEY)
make lint       # ruff + mypy
```

## Future work

- Postgres adapter (only `composition.py` changes — see `docs/architecture.md`)
- Pre-generation clarification node for ambiguous questions
- Streaming answers for large result sets
- Rate limiting and per-user auth for multi-tenant deployment
