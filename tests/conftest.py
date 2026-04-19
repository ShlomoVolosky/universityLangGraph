"""Shared fixtures: in-memory DB, fake LLM, noop tracer, test graph factory."""

import sqlite3
from pathlib import Path

import pytest

from university_qa.adapters.fake_llm import FakeLlmClient
from university_qa.adapters.noop_tracer import NoopTracer
from university_qa.adapters.sqlite_executor import SqliteExecutor
from university_qa.adapters.sqlite_schema import SqliteSchemaProvider
from university_qa.agent.graph import build_graph
from university_qa.agent.nodes import Dependencies

_SCHEMA = (Path(__file__).parent.parent / "db" / "schema.sql").read_text()

# Compact deterministic seed — fixed IDs, covers all join paths
_TEST_SEED = """
INSERT INTO teachers VALUES
    (1, 'Dr. Alice Nguyen',  'Computer Science'),
    (2, 'Prof. Bob Carter',  'Mathematics'),
    (3, 'Dr. Carol Diaz',    'Computer Science');

INSERT INTO students VALUES
    (1, 'Emma Wilson',    2022),
    (2, 'Liam Johnson',   2022),
    (3, 'Olivia Brown',   2023),
    (4, 'Noah Davis',     2023),
    (5, 'Ava Martinez',   2024);

INSERT INTO courses VALUES
    (1, 'CS101: Intro to Programming', 3),
    (2, 'MA201: Calculus I',           4),
    (3, 'CS301: Data Structures',      3),
    (4, 'CS401: Operating Systems',    3);

INSERT INTO course_offerings VALUES
    (1, 1, 1, '2024-Fall'),
    (2, 2, 2, '2024-Fall'),
    (3, 1, 1, '2025-Spring'),
    (4, 3, 1, '2025-Spring');

INSERT INTO enrollments VALUES
    (1,  1, 1, 88.0),
    (2,  2, 1, 74.5),
    (3,  3, 1, 91.0),
    (4,  4, 1, 63.0),
    (5,  5, 1, 77.5),
    (6,  1, 2, 85.0),
    (7,  2, 2, 70.0),
    (8,  3, 2, 92.0),
    (9,  1, 3, 80.0),
    (10, 2, 3, 68.0),
    (11, 3, 3, NULL),
    (12, 4, 4, 75.0),
    (13, 5, 4, 88.0);
"""


@pytest.fixture()
def in_memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(_SCHEMA)
    conn.executescript(_TEST_SEED)
    return conn


@pytest.fixture()
def noop_tracer() -> NoopTracer:
    return NoopTracer()


@pytest.fixture()
def fake_llm():
    """Factory: takes a {pattern: response} dict and returns FakeLlmClient."""

    def _factory(responses: dict[str, str]) -> FakeLlmClient:
        return FakeLlmClient(responses)

    return _factory


@pytest.fixture()
def test_graph(in_memory_db: sqlite3.Connection, noop_tracer: NoopTracer):
    """Factory: takes a FakeLlmClient and returns a compiled graph."""

    def _factory(llm: FakeLlmClient):
        deps = Dependencies(
            schema_provider=SqliteSchemaProvider(in_memory_db),
            executor=SqliteExecutor(in_memory_db),
            llm=llm,
            tracer=noop_tracer,
        )
        return build_graph(deps)

    return _factory
