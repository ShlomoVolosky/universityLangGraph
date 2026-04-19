GENERATE_SQL_SYSTEM = """\
You are a SQL expert. Given a database schema and a natural-language question, \
write a single SQL SELECT query that answers the question.

Rules (non-negotiable):
- Output ONLY the raw SQL — no markdown fences, no prose, no explanation.
- The query MUST be a SELECT statement. DDL and DML are forbidden.
- Use explicit JOINs (never implicit comma joins).
- Use table aliases for all multi-table queries.
- Target dialect: {dialect}
- Never invent columns or tables not present in the schema.

Schema:
{schema}
"""

GENERATE_SQL_USER = """\
{prior_attempts_block}Question: {question}
"""

_PRIOR_ATTEMPTS_HEADER = """\
Your previous attempt(s) failed. Study each error and produce a corrected query.

{attempts}
"""

_PRIOR_ATTEMPT_ENTRY = "Attempt {n}:\n  SQL: {sql}\n  Error: {error}\n"

FORMAT_ANSWER_SYSTEM = """\
You are a helpful assistant. Answer the user's question using ONLY the data \
provided in the query results below. Cite exact numbers from the results. \
Do not invent or infer values not present in the data. \
Keep your answer to 1–3 sentences.
"""

FORMAT_ANSWER_USER = """\
Question: {question}

Query results{truncation_note}:
{rows_json}
"""


def build_generate_sql_user(
    question: str,
    prior_attempts: list[tuple[str, str]],
) -> str:
    if not prior_attempts:
        prior_block = ""
    else:
        entries = "".join(
            _PRIOR_ATTEMPT_ENTRY.format(n=i + 1, sql=sql, error=err)
            for i, (sql, err) in enumerate(prior_attempts)
        )
        prior_block = _PRIOR_ATTEMPTS_HEADER.format(attempts=entries)
    return GENERATE_SQL_USER.format(prior_attempts_block=prior_block, question=question)


def build_format_answer_user(
    question: str, rows_json: str, truncated: bool, total_rows: int = 0
) -> str:
    note = f" (first 50 of {total_rows} rows shown)" if truncated else ""
    return FORMAT_ANSWER_USER.format(
        question=question,
        truncation_note=note,
        rows_json=rows_json,
    )
