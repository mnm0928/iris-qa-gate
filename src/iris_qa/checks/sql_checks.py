from __future__ import annotations

from typing import Any

from psycopg import sql

from iris_qa.checks.base import CANONICAL_ORDER, Check, CheckContext, ProfileError, register
from iris_qa.model import Outcome, QuarantineEntry, Violation


@register
class KeyUniqueness(Check):
    """Identifiers must be present and unique within a country.

    ``on_duplicate = "quarantine"`` withholds every member of a duplicated key group
    from promotion, never picking a winner, so the outcome does not depend on load
    order. Exceeding ``max_quarantine_ratio`` of the batch blocks instead.
    """

    type = "key_uniqueness"
    implementation = "sql"
    issues = {
        "missing_key": Outcome.BLOCK,
        "duplicate_key": Outcome.BLOCK,
        "duplicate_key_quarantined": Outcome.WARN,
        "quarantine_limit_exceeded": Outcome.BLOCK,
    }
    optional_params = {"on_duplicate": "block", "max_quarantine_ratio": 0.05}

    def validate(self) -> None:
        if self.params["on_duplicate"] not in ("block", "quarantine"):
            raise ProfileError(f"{self.check_id}: on_duplicate must be 'block' or 'quarantine'")

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        key = ctx.dataset.key_ident
        rows = ctx.query(
            sql.SQL(
                """
                SELECT country_code, {key} AS key, count(*) AS n,
                       ({key} IS NULL OR btrim({key}) = '') AS missing
                FROM {table}
                GROUP BY country_code, {key}
                HAVING count(*) > 1 OR {key} IS NULL OR btrim({key}) = ''
                ORDER BY country_code NULLS FIRST, {key} NULLS FIRST
                """
            ).format(key=key, table=ctx.dataset.table)
        )
        total = ctx.query(sql.SQL("SELECT count(*) AS n FROM {}").format(ctx.dataset.table))[0]["n"]
        quarantine = self.params["on_duplicate"] == "quarantine"

        violations = []
        duplicated_rows = 0
        for r in rows:
            if r["missing"]:
                violations.append(self.violation("missing_key", r["country_code"], r["key"], rows=r["n"]))
            else:
                duplicated_rows += r["n"]
                issue = "duplicate_key_quarantined" if quarantine else "duplicate_key"
                violations.append(self.violation(issue, r["country_code"], r["key"], rows=r["n"]))

        ratio = duplicated_rows / total if total else 0.0
        if quarantine and ratio > self.params["max_quarantine_ratio"]:
            violations.append(
                self.violation(
                    "quarantine_limit_exceeded", None, None,
                    quarantined_rows=duplicated_rows, ratio=round(ratio, 4),
                    limit=self.params["max_quarantine_ratio"],
                )
            )
        return violations, {"rows_checked": total, "duplicated_rows": duplicated_rows, "policy": self.params["on_duplicate"]}

    def quarantine(self, violations: list[Violation]) -> list[QuarantineEntry]:
        return [
            QuarantineEntry(v.country_code, v.key, "duplicate_key")
            for v in violations
            if v.issue == "duplicate_key_quarantined"
        ]


@register
class GeometryContract(Check):
    """Canonical ``geom`` must be present, non-empty, valid, of an allowed type and in the dataset SRID."""

    type = "geometry"
    implementation = "sql"
    issues = {
        "missing_geometry": Outcome.BLOCK,
        "empty_geometry": Outcome.BLOCK,
        "wrong_srid": Outcome.BLOCK,
        "wrong_geometry_type": Outcome.BLOCK,
        "invalid_geometry": Outcome.BLOCK,
    }

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        ds = ctx.dataset
        rows = ctx.query(
            sql.SQL(
                """
                SELECT t.country_code, t.{key} AS key,
                       t.geom IS NULL AS missing,
                       ST_IsEmpty(t.geom) AS empty,
                       ST_SRID(t.geom) AS srid,
                       GeometryType(t.geom) AS geometry_type,
                       ST_IsValid(t.geom) AS valid,
                       CASE WHEN NOT ST_IsValid(t.geom) THEN ST_IsValidReason(t.geom) END AS reason
                FROM {table} t
                WHERE t.geom IS NULL
                   OR ST_IsEmpty(t.geom)
                   OR ST_SRID(t.geom) <> %(srid)s
                   OR GeometryType(t.geom) <> ALL(%(types)s)
                   OR NOT ST_IsValid(t.geom)
                ORDER BY {order}
                """
            ).format(key=ds.key_ident, table=ds.table, order=CANONICAL_ORDER.format(key=ds.key_ident)),
            {"srid": ds.srid, "types": list(ds.geometry_types)},
        )
        violations = []
        for r in rows:
            cc, key = r["country_code"], r["key"]
            if r["missing"]:
                violations.append(self.violation("missing_geometry", cc, key))
                continue
            if r["empty"]:
                violations.append(self.violation("empty_geometry", cc, key))
            if r["srid"] != ds.srid:
                violations.append(self.violation("wrong_srid", cc, key, srid=r["srid"], expected=ds.srid))
            if r["geometry_type"] not in ds.geometry_types:
                violations.append(
                    self.violation(
                        "wrong_geometry_type", cc, key,
                        geometry_type=r["geometry_type"], expected=list(ds.geometry_types),
                    )
                )
            if not r["valid"]:
                violations.append(self.violation("invalid_geometry", cc, key, reason=r["reason"]))
        return violations, {"srid": ds.srid, "allowed_types": list(ds.geometry_types)}


@register
class CountryScope(Check):
    """Rows must belong to an in-scope country and region, and lie inside that region.

    Containment is only evaluated for geometry the ``geometry`` check accepts, so a
    malformed shape is reported once, as a geometry defect, not twice.
    """

    type = "country_scope"
    implementation = "sql"
    issues = {
        "missing_country_code": Outcome.BLOCK,
        "country_out_of_scope": Outcome.BLOCK,
        "region_out_of_scope": Outcome.BLOCK,
        "geometry_outside_region": Outcome.BLOCK,
    }

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        ds = ctx.dataset
        rows = ctx.query(
            sql.SQL(
                """
                SELECT * FROM (
                    SELECT t.country_code, t.{key} AS key, t.region_code,
                           CASE
                               WHEN t.country_code IS NULL THEN 'missing_country_code'
                               WHEN NOT (t.country_code = ANY(%(countries)s)) THEN 'country_out_of_scope'
                               WHEN r.region_code IS NULL THEN 'region_out_of_scope'
                               WHEN t.geom IS NULL OR ST_IsEmpty(t.geom)
                                    OR ST_SRID(t.geom) <> ST_SRID(r.geom) OR NOT ST_IsValid(t.geom) THEN 'not_evaluated'
                               WHEN NOT ST_CoveredBy(t.geom, r.geom) THEN 'geometry_outside_region'
                           END AS issue,
                           CASE WHEN r.geom IS NOT NULL AND ST_SRID(t.geom) = ST_SRID(r.geom) AND ST_IsValid(t.geom)
                                THEN round(ST_Distance(t.geom, r.geom)::numeric, 1) END AS distance_to_region_m
                    FROM {table} t
                    LEFT JOIN ref.region r
                           ON r.country_code = t.country_code
                          AND r.region_code = t.region_code
                          AND r.region_code = ANY(%(regions)s)
                    ORDER BY {order}
                ) s
                WHERE s.issue IS NOT NULL
                """
            ).format(key=ds.key_ident, table=ds.table, order=CANONICAL_ORDER.format(key=ds.key_ident)),
            {"countries": list(ds.countries), "regions": list(ds.regions)},
        )
        violations = []
        not_evaluated = 0
        for r in rows:
            if r["issue"] == "not_evaluated":
                not_evaluated += 1
                continue
            detail: dict[str, Any] = {"region_code": r["region_code"]}
            if r["issue"] == "geometry_outside_region":
                detail["distance_to_region_m"] = float(r["distance_to_region_m"])
            violations.append(self.violation(r["issue"], r["country_code"], r["key"], **detail))
        return violations, {
            "countries": list(ds.countries),
            "regions": list(ds.regions),
            "containment_not_evaluated": not_evaluated,
        }


@register
class DuplicateRows(Check):
    """Distinct keys describing the same thing inflate totals (area, eco-points, counts).

    Rows are compared on ``columns`` (default: every non-key column); geometry is
    normalised and snapped to ``snap_grid`` metres so vertex order or float noise
    do not hide a duplicate. Same-key repeats are ``key_uniqueness``'s concern.
    """

    type = "duplicate_rows"
    implementation = "sql"
    issues = {"duplicate_record": Outcome.BLOCK}
    optional_params = {"columns": None, "snap_grid": 0.01}

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        ds = ctx.dataset
        available = ctx.columns()
        columns = self.params["columns"] or [c for c in available if c != ds.key]
        unknown = sorted(set(columns) - set(available))
        if unknown:
            raise ProfileError(f"{self.check_id}: unknown column(s) {unknown}")

        signature = [
            sql.SQL("ST_AsEWKB(ST_Normalize(ST_SnapToGrid(t.geom, %(grid)s)))")
            if c == "geom"
            else sql.SQL("t.{}").format(sql.Identifier(c))
            for c in columns
        ]
        rows = ctx.query(
            sql.SQL(
                """
                SELECT min(t.country_code) AS country_code,
                       array_agg(DISTINCT t.{key} ORDER BY t.{key}) AS keys,
                       count(*) AS n
                FROM {table} t
                GROUP BY {signature}
                HAVING count(DISTINCT t.{key}) > 1
                ORDER BY min(t.country_code), min(t.{key})
                """
            ).format(key=ds.key_ident, table=ds.table, signature=sql.SQL(", ").join(signature)),
            {"grid": self.params["snap_grid"]},
        )
        violations = [
            self.violation("duplicate_record", r["country_code"], r["keys"][0], duplicate_keys=r["keys"], rows=r["n"])
            for r in rows
        ]
        return violations, {"compared_columns": columns, "snap_grid_m": self.params["snap_grid"]}


@register
class ReferenceIntegrity(Check):
    """A foreign key must resolve in the referenced table within the same country."""

    type = "reference_integrity"
    implementation = "sql"
    issues = {"dangling_reference": Outcome.BLOCK}
    required_params = frozenset({"column", "ref_table", "ref_key"})

    def evaluate(self, ctx: CheckContext) -> tuple[list[Violation], dict[str, Any]]:
        ds = ctx.dataset
        column = sql.Identifier(self.params["column"])
        rows = ctx.query(
            sql.SQL(
                """
                SELECT t.country_code, t.{key} AS key, t.{column} AS ref
                FROM {table} t
                WHERE t.{column} IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM {ref_table} r
                      WHERE r.country_code = t.country_code AND r.{ref_key} = t.{column}
                  )
                ORDER BY {order}
                """
            ).format(
                key=ds.key_ident,
                column=column,
                table=ds.table,
                ref_table=sql.Identifier(*self.params["ref_table"].split(".")),
                ref_key=sql.Identifier(self.params["ref_key"]),
                order=CANONICAL_ORDER.format(key=ds.key_ident),
            )
        )
        violations = [
            self.violation(
                "dangling_reference", r["country_code"], r["key"],
                column=self.params["column"], value=r["ref"], ref_table=self.params["ref_table"],
            )
            for r in rows
        ]
        return violations, {"ref_table": self.params["ref_table"], "scoped_by": "country_code"}

