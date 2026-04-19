# Production Checklist

Concrete steps to harden this system for production. Organized by concern.

---

## Security

- **Read-only DB user.** Open the connection with the minimum required privilege. For SQLite: `file:{path}?mode=ro&uri=true` (already implemented). For Postgres: create a role with `GRANT SELECT ON ALL TABLES IN SCHEMA public TO university_qa_reader;` — no INSERT, UPDATE, DELETE, or DDL rights.
- **Rotate LLM API keys.** Store `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in a secrets manager (AWS Secrets Manager, HashiCorp Vault). Rotate every 90 days. Never commit to source control.
- **Non-SELECT hard stop is not the only line of defence.** The sqlglot validator catches known DML/DDL patterns; the read-only connection is the second layer. Audit both layers when upgrading sqlglot versions, since AST node types may change.
- **Prompt injection.** User questions are embedded in LLM prompts. Sanitize for control characters and excessively long inputs (cap at ~500 characters). Log questions that produce non-SELECT SQL for security review.
- **LangSmith traces contain query results.** Treat the `university-qa-dev` LangSmith project as sensitive — it may contain student grade data. Apply project-level access controls in LangSmith.

---

## Reliability

- **Retry with backoff on LLM errors.** `AnthropicLlmClient` already retries 429 / 5xx with exponential backoff (base 1 s, max 3 retries). Tune `max_retries` based on observed p99 latency.
- **SQLite timeout.** The executor sets a `progress_handler` to abort queries that run longer than 5 seconds. For Postgres, set `statement_timeout = 5000` on the connection.
- **`max_attempts` cap.** Default is 3. Do not raise above 5 — each retry is a full LLM round trip. Expose as `AgentState.max_attempts` so callers can lower it for latency-sensitive paths.
- **Connection pooling.** For SQLite, `check_same_thread=False` is set. For Postgres, use `psycopg2.pool.ThreadedConnectionPool` or `asyncpg` with a pool size matched to your concurrency target.
- **Health check endpoint.** If wrapping in a web server, add a `/healthz` route that opens the DB, runs `SELECT 1`, and returns 200. Attach it to your load balancer or k8s liveness probe.

---

## Scalability

- **Schema caching.** `SqliteSchemaProvider` caches the describe result after the first call. For a multi-process deployment, warm the cache at startup or share it via an in-process singleton — avoid re-introspecting the schema on every request.
- **Rate limiting.** Gate the `/ask` endpoint at your API gateway layer (e.g., nginx `limit_req`, AWS API Gateway usage plans). Target ≤10 RPS per user to cap LLM spend. Burst headroom of 3× for batch workloads.
- **Stateless graph.** Each `app.invoke()` is stateless — `AgentState` is constructed fresh per request. This means horizontal scaling (multiple processes or pods) requires no shared state.

---

## Observability

- **LangSmith auto-tracing.** Set `LANGSMITH_TRACING=true` in production. Every LangGraph node invocation is traced automatically with inputs, outputs, and latency. Pipe `LANGSMITH_PROJECT` to a per-environment project (`university-qa-prod`, `university-qa-staging`).
- **Custom spans.** `schema.fetch`, `sql.validate`, `sql.execute`, and `answer.format` spans surface per-node metrics. Monitor `sql.execute.duration_ms` for slow queries and `sql.validate.is_non_select` for security anomalies.
- **Structured logging.** Log `terminal_reason`, `attempts`, and question hash (not the full question — it may contain PII) at INFO level for every run. Alert on `terminal_reason=exhausted_retries` rate > 5%.
- **LLM cost tracking.** Track token usage per run via the Anthropic/OpenAI response metadata. Set a per-day budget alert in your cloud provider or LLM provider's dashboard.

---

## Deployment

- **Never commit `.env`.** `.gitignore` already excludes `.env` and `db/*.db`. Use CI environment variables or a secrets manager for all keys.
- **Database migrations.** `db/schema.sql` is the source of truth. For schema changes, write additive migrations (new columns with defaults, new tables). Never drop or rename columns without a multi-phase migration.
- **Read-only DB in containers.** Mount the SQLite file as a read-only volume (`readOnly: true` in Kubernetes, or `--mount type=bind,readonly` in Docker). Belt-and-suspenders on top of the `mode=ro` URI.
- **Model pinning.** Pin `anthropic_model` to a specific model version (e.g., `claude-sonnet-4-6`) in `.env`. Do not use `latest` aliases — model behaviour changes silently across versions.

---

## Cost

- **Prompt token budget.** `GENERATE_SQL_SYSTEM` is capped at ~400 tokens. `FORMAT_ANSWER_USER` truncates rows to 50 before sending. Monitor average prompt token count via LangSmith; raise an alert if it exceeds 1 500 tokens per run.
- **Retry cost.** Each retry adds one full LLM round trip. With `max_attempts=3` and 100 RPS, worst-case cost is 3× baseline. Track `attempts` distribution in LangSmith and alert if p95 > 1.5 attempts.
- **Caching.** The schema description is cached per `SqliteSchemaProvider` instance. For a Postgres deployment with infrequently-changing schemas, cache the `SchemaDescription` in Redis with a 5-minute TTL to avoid repeated `information_schema` queries.

---

## Data governance

- **Student grades are PII.** The system returns raw grade data in `rows`. Ensure your deployment complies with FERPA (US) or equivalent. Log the questions asked but not the rows returned.
- **Data retention.** LangSmith traces include query results. Set a LangSmith data retention policy (30 days for prod, 7 days for staging). Export and anonymize before long-term archival.
- **Audit trail.** Log every question, the generated SQL, `terminal_reason`, and `attempts` to a append-only audit table or a SIEM. Do not log the raw answer rows — they contain student data.
- **Access control.** The CLI has no authentication. Before exposing this system over a network, add an auth layer (JWT, API key, or OAuth) at the gateway. Map authenticated users to allowed question scopes (e.g., a student can only query their own records).
