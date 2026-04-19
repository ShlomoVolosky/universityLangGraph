#!/usr/bin/env python3
"""Creates db/university.db from schema.sql + seed.sql. Idempotent unless --force."""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "university.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "db" / "seed.sql"


def init_db(db_path: Path, *, force: bool = False) -> None:
    if db_path.exists():
        if not force:
            print(f"ERROR: {db_path} already exists. Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.executescript(SEED_PATH.read_text())
        conn.commit()
        print(f"Database created: {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialise the university SQLite database.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing DB file.")
    parser.add_argument("--db", default=str(DB_PATH), help="Output DB path.")
    args = parser.parse_args()
    init_db(Path(args.db), force=args.force)
