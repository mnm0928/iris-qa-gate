from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from psycopg import sql

from iris_qa.checks.base import Check, CheckContext, ProfileError, register
from iris_qa.model import Outcome, Violation

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _field_exprs(ctx: CheckContext, fields: list[str]) -> tuple[dict[str, sql.Composable], list[str]]:
    available = set(ctx.columns())
    exprs: dict[str, sql.Composable] = {}
    absent = []
    for f in fields:
        if f not in available:
            absent.append(f)
        elif f == "geom":
            exprs[f] = sql.SQL("CASE WHEN t.geom IS NOT NULL THEN 'present' END")
        else:
            exprs[f] = sql.SQL("t.{}").format(sql.Identifier(f))
    return exprs, absent


def _usable_geometry(ctx: CheckContext) -> sql.Composable:
    """Geometry the ``geometry`` check would accept; anything else is that check's finding."""
    return sql.SQL(
        "t.geom IS NOT NULL AND NOT ST_IsEmpty(t.geom) AND ST_SRID(t.geom) = {srid} "
        "AND GeometryType(t.geom) = ANY({types}) AND ST_IsValid(t.geom)"
    ).format(srid=sql.Literal(ctx.dataset.srid), types=sql.Literal(list(ctx.dataset.geometry_types)))


@register
class RequiredFields(Check):
    """Contracted attributes must exist as columns and be populated on every row."""

    type = "required_fields"
    implementation = "python"
    issues = {"missing_column": Outcome.BLOCK, "missing_required_value": Outcome.BLOCK}
    required_params = frozenset({"fields"})

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        exprs, absent = _field_exprs(ctx, self.params["fields"])
        violations = [self.violation("missing_column", None, None, field=f) for f in absent]
        rows = ctx.rows(exprs)
        for row in rows:
            for f in exprs:
                if is_missing(row[f]):
                    violations.append(self.violation("missing_required_value", row["country_code"], row["_key"], field=f))
        return violations, {"fields": self.params["fields"], "rows_checked": len(rows)}


@register
class OptionalFields(Check):
    """Missing enrichment stays NULL and is surfaced as *unknown*; it can never block.

    If an attribute is important enough to stop a launch it is not optional and
    belongs in ``required_fields`` instead.
    """

    type = "optional_fields"
    implementation = "python"
    issues = {"missing_optional_value": Outcome.WARN, "missing_column": Outcome.WARN}
    max_severity = {"missing_optional_value": Outcome.WARN, "missing_column": Outcome.WARN}
    required_params = frozenset({"fields"})

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        exprs, absent = _field_exprs(ctx, self.params["fields"])
        violations = [self.violation("missing_column", None, None, field=f) for f in absent]
        rows = ctx.rows(exprs)
        unknown = {f: 0 for f in exprs}
        for row in rows:
            for f in exprs:
                if is_missing(row[f]):
                    unknown[f] += 1
                    violations.append(
                        self.violation("missing_optional_value", row["country_code"], row["_key"], field=f, value="unknown")
                    )
        coverage = {
            f: {"unknown": n, "known": len(rows) - n, "unknown_ratio": round(n / len(rows), 4) if rows else 0.0}
            for f, n in unknown.items()
        }
        return violations, {"rows_checked": len(rows), "coverage": coverage, "imputation": "none"}

    def describe(self, outcome: Outcome, counts: dict[str, int], details: dict[str, Any]) -> str:
        gaps = [f"{f} unknown on {c['unknown']}/{c['unknown'] + c['known']} rows"
                for f, c in details["coverage"].items() if c["unknown"]]
        if not gaps and not counts:
            return "no violations"
        return "warn: " + "; ".join(gaps or [f"{n} {i}" for i, n in counts.items()]) + " (kept NULL, not imputed)"


@register
class SourceDate(Check):
    """Every row carries an ISO source date that is not in the future and, optionally, not stale."""

    type = "source_date"
    implementation = "python"
    issues = {
        "missing_source_date": Outcome.BLOCK,
        "unparseable_source_date": Outcome.BLOCK,
        "future_source_date": Outcome.BLOCK,
        "stale_source_date": Outcome.WARN,
    }
    optional_params = {"column": "source_date", "max_age_days": None}

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        column = self.params["column"]
        max_age = self.params["max_age_days"]
        oldest_allowed = ctx.as_of - timedelta(days=max_age) if max_age is not None else None
        rows = ctx.rows({"value": sql.SQL("t.{}::text").format(sql.Identifier(column))})

        violations = []
        parsed: list[date] = []
        for row in rows:
            cc, key, raw = row["country_code"], row["_key"], row["value"]
            if is_missing(raw):
                violations.append(self.violation("missing_source_date", cc, key))
                continue
            value = _parse_iso_date(raw.strip())
            if value is None:
                violations.append(self.violation("unparseable_source_date", cc, key, value=raw))
                continue
            parsed.append(value)
            if value > ctx.as_of:
                violations.append(self.violation("future_source_date", cc, key, value=raw, as_of=ctx.as_of.isoformat()))
            elif oldest_allowed and value < oldest_allowed:
                violations.append(
                    self.violation("stale_source_date", cc, key, value=raw, age_days=(ctx.as_of - value).days, max_age_days=max_age)
                )
        return violations, {
            "as_of": ctx.as_of.isoformat(),
            "max_age_days": max_age,
            "oldest": min(parsed).isoformat() if parsed else None,
            "newest": max(parsed).isoformat() if parsed else None,
        }


def _parse_iso_date(raw: str) -> date | None:
    if not ISO_DATE.match(raw):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


@register
class DeclaredArea(Check):
    """A declared area must agree with the geometry it describes (planar m² in the dataset CRS).

    ``mode = "equal"`` compares within ``rel_tolerance``; ``mode = "at_most"`` only
    rejects declared values exceeding the geometry, e.g. an eligible sub-area.
    """

    type = "declared_area"
    implementation = "python"
    issues = {
        "non_positive_area": Outcome.BLOCK,
        "area_mismatch": Outcome.BLOCK,
        "area_exceeds_geometry": Outcome.BLOCK,
    }
    required_params = frozenset({"column"})
    optional_params = {"mode": "equal", "rel_tolerance": 0.01}

    def validate(self) -> None:
        if self.params["mode"] not in ("equal", "at_most"):
            raise ProfileError(f"{self.check_id}: mode must be 'equal' or 'at_most'")

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        column = self.params["column"]
        tol = Decimal(str(self.params["rel_tolerance"]))
        rows = ctx.rows({
            "declared": sql.SQL("t.{}").format(sql.Identifier(column)),
            "geometry_area": sql.SQL("CASE WHEN {} THEN ST_Area(t.geom)::numeric END").format(_usable_geometry(ctx)),
        })
        violations = []
        skipped = 0
        for row in rows:
            cc, key, declared, actual = row["country_code"], row["_key"], row["declared"], row["geometry_area"]
            if declared is None:
                continue
            if declared <= 0 and self.params["mode"] == "equal":
                violations.append(self.violation("non_positive_area", cc, key, declared_m2=float(declared)))
                continue
            if actual is None:
                skipped += 1
                continue
            detail = {"declared_m2": float(declared), "geometry_m2": round(float(actual), 2)}
            if self.params["mode"] == "equal":
                if not actual or abs(declared - actual) / actual > tol:
                    deviation = round(float(abs(declared - actual) / actual), 4) if actual else None
                    violations.append(self.violation("area_mismatch", cc, key, deviation=deviation, **detail))
            elif declared > actual * (1 + tol):
                violations.append(self.violation("area_exceeds_geometry", cc, key, **detail))
        return violations, {
            "column": column,
            "mode": self.params["mode"],
            "rel_tolerance": float(tol),
            "not_evaluated_bad_geometry": skipped,
        }


@register
class ProductConsistency(Check):
    """``result`` must equal the product of ``factors``; ``expected`` pins contractual constants."""

    type = "product_consistency"
    implementation = "python"
    issues = {"product_mismatch": Outcome.BLOCK, "unexpected_constant": Outcome.BLOCK}
    required_params = frozenset({"result", "factors"})
    optional_params = {"abs_tolerance": 0.5, "expected": {}}

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        result_col, factors, expected = self.params["result"], self.params["factors"], self.params["expected"]
        tol = Decimal(str(self.params["abs_tolerance"]))
        columns = [result_col, *factors, *[c for c in expected if c not in factors]]
        rows = ctx.rows({c: sql.SQL("t.{}").format(sql.Identifier(c)) for c in columns})

        violations = []
        for row in rows:
            cc, key = row["country_code"], row["_key"]
            for col, value in expected.items():
                if row[col] is not None and row[col] != Decimal(str(value)):
                    violations.append(self.violation("unexpected_constant", cc, key, column=col, value=float(row[col]), expected=value))
            if any(row[c] is None for c in [result_col, *factors]):
                continue
            product = Decimal(1)
            for f in factors:
                product *= row[f]
            if abs(row[result_col] - product) > tol:
                violations.append(
                    self.violation(
                        "product_mismatch", cc, key,
                        formula=f"{result_col} = {' * '.join(factors)}",
                        declared=float(row[result_col]), computed=float(product),
                        inputs={f: float(row[f]) for f in factors},
                    )
                )
        return violations, {"formula": f"{result_col} = {' * '.join(factors)}", "abs_tolerance": float(tol), "expected": expected}


@register
class Domain(Check):
    """Populated values must fall in an allowed set and/or numeric range."""

    type = "domain"
    implementation = "python"
    issues = {"value_not_allowed": Outcome.BLOCK, "value_out_of_range": Outcome.BLOCK}
    required_params = frozenset({"column"})
    optional_params = {"allowed": None, "min": None, "max": None}

    def validate(self) -> None:
        if self.params["allowed"] is None and self.params["min"] is None and self.params["max"] is None:
            raise ProfileError(f"{self.check_id}: set at least one of allowed/min/max")

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        column, allowed, lo, hi = (self.params[k] for k in ("column", "allowed", "min", "max"))
        rows = ctx.rows({"value": sql.SQL("t.{}").format(sql.Identifier(column))})
        violations = []
        for row in rows:
            value = row["value"]
            if is_missing(value):
                continue
            if allowed is not None and value not in allowed:
                violations.append(self.violation("value_not_allowed", row["country_code"], row["_key"], column=column, value=value, allowed=allowed))
            elif (lo is not None and value < Decimal(str(lo))) or (hi is not None and value > Decimal(str(hi))):
                violations.append(self.violation("value_out_of_range", row["country_code"], row["_key"], column=column, value=float(value), min=lo, max=hi))
        return violations, {"column": column, "allowed": allowed, "min": lo, "max": hi}
