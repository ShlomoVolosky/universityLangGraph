import sqlite3

from university_qa.domain.types import SchemaDescription
from university_qa.ports.schema_provider import SchemaProvider


class SqliteSchemaProvider(SchemaProvider):
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._cache: SchemaDescription | None = None

    def describe(self) -> SchemaDescription:
        if self._cache is None:
            self._cache = self._build()
        return self._cache

    def refresh(self) -> None:
        self._cache = None

    def _build(self) -> SchemaDescription:
        cur = self._conn.cursor()

        # Collect table names (excluding SQLite internals)
        cur.execute(
            "SELECT name FROM sqlite_master"
            " WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        table_names = [row[0] for row in cur.fetchall()]

        # Build column descriptions per table
        table_lines: list[str] = []
        for table in table_names:
            cur.execute(f"PRAGMA table_info({table})")
            columns = cur.fetchall()
            col_parts: list[str] = []
            for col in columns:
                # col: (cid, name, type, notnull, dflt_value, pk)
                cid, name, col_type, notnull, _, pk = col
                part = f"{name} {col_type}"
                if pk:
                    part += " PK"
                elif notnull:
                    part += " NOT NULL"
                col_parts.append(part)
            table_lines.append(f"  {table}({', '.join(col_parts)})")

        # Collect foreign key relationships
        fk_lines: list[str] = []
        for table in table_names:
            cur.execute(f"PRAGMA foreign_key_list({table})")
            for fk in cur.fetchall():
                # fk: (id, seq, table, from, to, on_update, on_delete, match)
                _, _, ref_table, from_col, to_col, *_ = fk
                fk_lines.append(f"  {table}.{from_col} -> {ref_table}.{to_col}")

        parts = ["Dialect: sqlite", "", "Tables:"]
        parts.extend(table_lines)
        if fk_lines:
            parts += ["", "Relationships:"]
            parts.extend(fk_lines)

        return SchemaDescription(text="\n".join(parts), table_names=table_names)
