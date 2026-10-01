from __future__ import annotations

import csv
import os
from pathlib import Path

import psycopg
from psycopg import sql

DEFAULT_DSN = "postgresql://iris:iris@localhost:55432/iris"
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def dsn() -> str:
    return os.environ.get("IRIS_QA_DSN", DEFAULT_DSN)


def connect(conninfo: str | None = None) -> psycopg.Connection:
    return psycopg.connect(conninfo or dsn(), autocommit=True)


def migrate(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS public.schema_migrations "
        "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    applied = {r[0] for r in conn.execute("SELECT version FROM public.schema_migrations")}
    newly_applied = []
    for path in sorted(directory.glob("*.sql")):
        if path.stem in applied:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("INSERT INTO public.schema_migrations (version) VALUES (%s)", (path.stem,))
        newly_applied.append(path.stem)
    return newly_applied


def load_csv(conn: psycopg.Connection, table: str, path: Path) -> int:
    """Replace a staging table with a CSV batch. Empty cells load as NULL; ``geom`` is EWKT."""
    with path.open(newline="") as fh:
        header = next(csv.reader(fh))
    target = sql.Identifier(*table.split("."))
    columns = sql.SQL(", ").join(sql.Identifier(c) for c in header)
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE {}").format(target))
        with cur.copy(
            sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')").format(target, columns)
        ) as copy, path.open("rb") as fh:
            while chunk := fh.read(65536):
                copy.write(chunk)
        cur.execute(sql.SQL("SELECT count(*) FROM {}").format(target))
        return cur.fetchone()[0]
