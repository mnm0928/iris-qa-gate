from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from iris_qa.checks import CheckContext
from iris_qa.checks.base import error_result
from iris_qa.model import Outcome, RunReport
from iris_qa.profile import Profile


def run(
    conn: psycopg.Connection,
    profile: Profile,
    as_of: date,
    *,
    promote: bool = False,
    evidence_limit: int = 25,
) -> RunReport:
    """Evaluate a profile against its staging table, persist the run and optionally promote.

    Evaluation, promotion and persistence share one snapshot and one transaction; a
    BLOCK decision is recorded but never promoted.
    """
    ds = profile.dataset
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        conn.execute(sql.SQL("LOCK TABLE {} IN SHARE MODE").format(ds.table))

        started_at = datetime.now(UTC)
        row_count, fingerprint = _fingerprint(conn, profile)
        ctx = CheckContext(conn=conn, dataset=ds, as_of=as_of, evidence_limit=evidence_limit)
        results = []
        for check in profile.checks:
            try:
                with conn.transaction():
                    results.append(check.run(ctx))
            except Exception as exc:  # noqa: BLE001 - any failure to evaluate must block
                results.append(error_result(check, exc))

        report = RunReport(
            run_id=str(uuid.uuid4()),
            dataset=ds.name,
            profile_name=profile.name,
            profile_sha256=profile.sha256,
            as_of=as_of,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            row_count=row_count,
            dataset_fingerprint=fingerprint,
            results=results,
        )
        _insert_run(conn, report)
        quarantined = _quarantine(conn, profile, report)
        if promote and report.decision is not Outcome.BLOCK:
            _promote(conn, profile, report)
            report.promoted = True
        conn.execute(
            "UPDATE qa.run SET promoted = %s, quarantined_rows = %s, summary = %s WHERE run_id = %s",
            (report.promoted, quarantined, Jsonb(report.to_dict(), dumps=_dumps), report.run_id),
        )
    return report


def load_report(conn: psycopg.Connection, run_id: str) -> dict | None:
    row = conn.execute("SELECT summary FROM qa.run WHERE run_id = %s", (run_id,)).fetchone()
    return row[0] if row else None


def latest_runs(conn: psycopg.Connection, limit: int = 20) -> list[tuple]:
    return conn.execute(
        "SELECT run_id, dataset, decision, promoted, row_count, quarantined_rows, started_at "
        "FROM qa.run ORDER BY started_at DESC LIMIT %s",
        (limit,),
    ).fetchall()


def _fingerprint(conn: psycopg.Connection, profile: Profile) -> tuple[int, str]:
    row = conn.execute(
        sql.SQL(
            "SELECT count(*), md5(coalesce(string_agg(md5(t::text), '' ORDER BY md5(t::text)), '')) FROM {} t"
        ).format(profile.dataset.table)
    ).fetchone()
    return row[0], row[1]


def _insert_run(conn: psycopg.Connection, report: RunReport) -> None:
    conn.execute(
        """
        INSERT INTO qa.run (run_id, dataset, profile_name, profile_sha256, as_of, started_at, finished_at,
                            row_count, dataset_fingerprint, decision, summary)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '{}')
        """,
        (
            report.run_id, report.dataset, report.profile_name, report.profile_sha256, report.as_of,
            report.started_at, report.finished_at, report.row_count, report.dataset_fingerprint,
            report.decision.value,
        ),
    )
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO qa.check_result (run_id, seq, check_id, check_type, implementation, outcome,
                                         violation_count, message, evidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    report.run_id, seq, r.check_id, r.check_type, r.implementation, r.outcome.value,
                    r.violation_count, r.message,
                    Jsonb({"issue_counts": r.issue_counts, "details": r.details,
                           "samples": r.evidence, "truncated": r.evidence_truncated}, dumps=_dumps),
                )
                for seq, r in enumerate(report.results, start=1)
            ],
        )


def _quarantine(conn: psycopg.Connection, profile: Profile, report: RunReport) -> int:
    entries = report.quarantine
    if not entries:
        return 0
    ds = profile.dataset
    cur = conn.execute(
        sql.SQL(
            """
            INSERT INTO qa.quarantine (run_id, dataset, country_code, record_key, reason, row_data)
            SELECT %(run_id)s, %(dataset)s, s.country_code, s.{key}, q.reason,
                   (to_jsonb(s) - 'geom') || jsonb_build_object('geom', ST_AsEWKT(s.geom))
            FROM {table} s
            JOIN unnest(%(cc)s::text[], %(keys)s::text[], %(reasons)s::text[]) AS q(cc, k, reason)
              ON q.cc = s.country_code AND q.k = s.{key}
            ORDER BY s.country_code, s.{key}, md5(s::text)
            """
        ).format(key=ds.key_ident, table=ds.table),
        {
            "run_id": report.run_id,
            "dataset": ds.name,
            "cc": [e.country_code for e in entries],
            "keys": [e.key for e in entries],
            "reasons": [e.reason for e in entries],
        },
    )
    return cur.rowcount


def _promote(conn: psycopg.Connection, profile: Profile, report: RunReport) -> int:
    """Replace the in-scope country slices of the curated table with this batch, minus quarantine.

    Values are cast to the curated column types, so the strict curated constraints are
    a second line of defence: nothing is coerced, defaulted or imputed on the way in.
    """
    ds = profile.dataset
    curated = sql.Identifier(*ds.curated_table.split("."))
    columns = conn.execute(
        """
        SELECT a.attname, format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped AND a.attname <> 'qa_run_id'
        ORDER BY a.attnum
        """,
        (ds.curated_table,),
    ).fetchall()
    entries = report.quarantine
    conn.execute(
        sql.SQL("DELETE FROM {} WHERE country_code = ANY(%s)").format(curated), (list(ds.countries),)
    )
    cur = conn.execute(
        sql.SQL(
            """
            INSERT INTO {curated} ({columns}, qa_run_id)
            SELECT {casts}, %(run_id)s
            FROM {table} s
            WHERE NOT EXISTS (
                SELECT 1 FROM unnest(%(cc)s::text[], %(keys)s::text[]) AS q(cc, k)
                WHERE q.cc = s.country_code AND q.k = s.{key}
            )
            """
        ).format(
            curated=curated,
            columns=sql.SQL(", ").join(sql.Identifier(name) for name, _ in columns),
            casts=sql.SQL(", ").join(
                sql.SQL("CAST(s.{} AS {})").format(sql.Identifier(name), sql.SQL(type_)) for name, type_ in columns
            ),
            table=ds.table,
            key=ds.key_ident,
        ),
        {
            "run_id": report.run_id,
            "cc": [e.country_code for e in entries],
            "keys": [e.key for e in entries],
        },
    )
    return cur.rowcount


def _dumps(obj) -> str:
    return json.dumps(obj, default=str, sort_keys=True)
