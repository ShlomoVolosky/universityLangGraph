# LangSmith Trace Exports

Three representative runs from the `university-qa-dev` project.
All traces include LangGraph auto-spans (node-level inputs/outputs/latency)
plus the custom sub-spans added via the `Tracer` port:
`schema.fetch`, `sql.validate`, `sql.execute`, `answer.format`,
and the `retry` / `terminal` events.

---

## 1. Happy path — 3-table join

**Question:** "Which student has the highest average grade across all their courses?"

**SQL generated:**
```sql
SELECT s.name, AVG(e.grade) AS avg_grade
FROM students s
JOIN enrollments e ON s.id = e.student_id
GROUP BY s.id, s.name
ORDER BY avg_grade DESC
LIMIT 1
```

**Answer:** Emma Wilson — average grade 86.75

**Trace:**
https://eu.smith.langchain.com/o/-/projects/p/4fd3a04a-1c4f-4195-90ef-1452ac079118/r/13ff3335-2e3d-4eac-928f-237eae988a34

---

## 2. Retry scenario — bad SQL on attempt 1, success on attempt 2

**Question:** "How many students are there?"

**Attempt 1:** `SELECT * FROM nonexistent_table_xyz` → execution error (table does not exist)

**Attempt 2:** `SELECT COUNT(*) AS cnt FROM students` → 15 rows

**Result:** `terminal_reason=ok`, `attempts=2`, `prior_attempts` length 1

**Trace:**
https://eu.smith.langchain.com/o/-/projects/p/4fd3a04a-1c4f-4195-90ef-1452ac079118/r/ebe8bb7e-41fb-4c2c-8829-864030dc6b46

---

## 3. Rejected non-SELECT

**Question:** "drop the students table"

**SQL generated:** `DROP TABLE students`

**Result:** `terminal_reason=rejected_non_select`, `attempts=1`, no execution,
fixed refusal message returned immediately (no retry, no LLM format call).

**Trace:**
https://eu.smith.langchain.com/o/-/projects/p/4fd3a04a-1c4f-4195-90ef-1452ac079118/r/2938853d-2c5c-43cb-bfc1-84c7e4ee3d75

---

## What to look for in the traces

| Custom span / event | Where it fires | Key dimensions |
|---|---|---|
| `schema.fetch` span | `load_schema` node | `table_count`, `total_column_count` |
| `sql.validate` event | `validate_sql` node | `ok`, `is_non_select`, `error_count` |
| `sql.execute` span | `execute_sql` node | `row_count`, `duration_ms`, `succeeded` |
| `answer.format` span | `format_answer` node | `input_row_count`, `truncated` |
| `retry` event | `retry_or_fail` node | `attempt`, `last_error` |
| `terminal` event | `retry_or_fail` / `reject_non_select` nodes | `terminal_reason` |
