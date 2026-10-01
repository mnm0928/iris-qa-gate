from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar, Literal

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from iris_qa.model import CheckResult, Outcome, QuarantineEntry, Violation


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    staging_table: str
    curated_table: str
    key: str
    countries: tuple[str, ...]
    regions: tuple[str, ...]
    srid: int
    geometry_types: tuple[str, ...]

    @property
    def table(self) -> sql.Identifier:
        return sql.Identifier(*self.staging_table.split("."))

    @property
    def key_ident(self) -> sql.Identifier:
        return sql.Identifier(self.key)


@dataclass
class CheckContext:
    conn: psycopg.Connection
    dataset: DatasetSpec
    as_of: date
    evidence_limit: int

    def query(self, query: sql.Composable, params: Any = None) -> list[dict[str, Any]]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def columns(self) -> list[str]:
        schema, table = self.dataset.staging_table.split(".")
        rows = self.query(
            sql.SQL(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position"
            ),
            (schema, table),
        )
        return [r["column_name"] for r in rows]

    def rows(self, select: dict[str, sql.Composable], where: sql.Composable | None = None) -> list[dict[str, Any]]:
        """Fetch rows in the dataset's canonical, deterministic order."""
        items = [sql.SQL("t.country_code"), sql.SQL("t.{} AS _key").format(self.dataset.key_ident)]
        items += [sql.SQL("{} AS {}").format(expr, sql.Identifier(alias)) for alias, expr in select.items()]
        return self.query(
            sql.SQL("SELECT {items} FROM {table} t {where} ORDER BY {order}").format(
                items=sql.SQL(", ").join(items),
                table=self.dataset.table,
                where=sql.SQL("WHERE ") + where if where is not None else sql.SQL(""),
                order=CANONICAL_ORDER.format(key=self.dataset.key_ident),
            )
        )


CANONICAL_ORDER = sql.SQL("t.country_code NULLS FIRST, t.{key} NULLS FIRST, md5(t::text)")

REGISTRY: dict[str, type[Check]] = {}


def register(cls: type[Check]) -> type[Check]:
    if cls.type in REGISTRY:
        raise RuntimeError(f"duplicate check type {cls.type!r}")
    REGISTRY[cls.type] = cls
    return cls


class Check(ABC):
    """A single acceptance rule.

    Subclasses declare the issues they can raise with a default severity. Profiles
    may re-grade issues via a ``severity`` table, except those in ``max_severity``
    caps, which encode semantics a profile must not override.
    """

    type: ClassVar[str]
    implementation: ClassVar[Literal["sql", "python"]]
    issues: ClassVar[dict[str, Outcome]]
    max_severity: ClassVar[dict[str, Outcome]] = {}
    required_params: ClassVar[frozenset[str]] = frozenset()
    optional_params: ClassVar[dict[str, Any]] = {}

    def __init__(self, check_id: str, params: dict[str, Any], severity: dict[str, str]):
        unknown = set(params) - self.required_params - set(self.optional_params)
        if unknown:
            raise ProfileError(f"{check_id}: unknown parameter(s) {sorted(unknown)}")
        missing = self.required_params - set(params)
        if missing:
            raise ProfileError(f"{check_id}: missing parameter(s) {sorted(missing)}")
        self.check_id = check_id
        self.params = {**self.optional_params, **params}
        self.severities = dict(self.issues)
        for issue, level in severity.items():
            if issue not in self.issues:
                raise ProfileError(f"{check_id}: unknown issue {issue!r} in severity table")
            try:
                outcome = Outcome(level.upper())
            except ValueError:
                raise ProfileError(f"{check_id}: invalid severity {level!r} for {issue!r}") from None
            cap = self.max_severity.get(issue)
            if cap is not None and outcome.rank > cap.rank:
                raise ProfileError(
                    f"{check_id}: issue {issue!r} may be graded at most {cap.value}, not {outcome.value}"
                )
            self.severities[issue] = outcome
        self.validate()

    def validate(self) -> None:
        pass

    @abstractmethod
    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        """Return violations (in canonical order) and free-form details."""

    def quarantine(self, violations: list[Violation]) -> list[QuarantineEntry]:
        return []

    def violation(self, issue: str, country_code: str | None, key: str | None, **detail: Any) -> Violation:
        return Violation(issue, self.severities[issue], country_code, key, detail)

    def run(self, ctx: CheckContext) -> CheckResult:
        violations, details = self.evaluate(ctx)
        outcome = Outcome.worst(v.severity for v in violations)
        counts = dict(sorted(Counter(v.issue for v in violations).items()))
        return CheckResult(
            check_id=self.check_id,
            check_type=self.type,
            implementation=self.implementation,
            outcome=outcome,
            message=self.describe(outcome, counts, details),
            violation_count=len(violations),
            issue_counts=counts,
            evidence=[v.as_evidence() for v in violations[: ctx.evidence_limit]],
            evidence_truncated=len(violations) > ctx.evidence_limit,
            details=details,
            quarantine=self.quarantine(violations),
        )

    def describe(self, outcome: Outcome, counts: dict[str, int], details: dict[str, Any]) -> str:
        if not counts:
            return "no violations"
        parts = ", ".join(f"{n} {issue}" for issue, n in counts.items())
        return f"{outcome.value.lower()}: {parts}"


def error_result(check: Check, exc: Exception) -> CheckResult:
    """A check that cannot run must fail closed."""
    return CheckResult(
        check_id=check.check_id,
        check_type=check.type,
        implementation=check.implementation,
        outcome=Outcome.BLOCK,
        message=f"check could not be evaluated: {type(exc).__name__}: {exc}".strip(),
        violation_count=0,
        issue_counts={"check_error": 1},
        evidence=[{"issue": "check_error", "severity": "BLOCK", "error": str(exc).strip()}],
        evidence_truncated=False,
    )
