"""The four acceptance criteria from the IRIS-CAND-06 brief."""

from __future__ import annotations

import pytest

from conftest import BOWTIE, X0, Y0, parcel, peat, site, square
from iris_qa.model import Outcome


class TestBlockingAndWarningAreDistinguishable:
    def test_run_separates_blocking_from_warning_checks(self, run_qa):
        report = run_qa("parcels", [parcel(1, soil_type=None), parcel(2, geom=BOWTIE)])
        data = report.to_dict()

        assert report.decision is Outcome.BLOCK
        assert data["blocking_checks"] == ["geometry"]
        assert data["warning_checks"] == ["optional_fields"]
        assert report.result("optional_fields").outcome is Outcome.WARN
        assert report.result("geometry").outcome is Outcome.BLOCK

    def test_every_evidence_row_carries_its_own_severity(self, run_qa):
        report = run_qa("parcels", [parcel(1, soil_type=None), parcel(2, geom=BOWTIE)])

        assert report.result("optional_fields").evidence[0]["severity"] == "WARN"
        assert report.result("geometry").evidence[0]["severity"] == "BLOCK"

    def test_warn_only_run_is_promotable_and_block_is_not(self, run_qa):
        warn = run_qa("parcels", [parcel(1, soil_type=None)], promote=True)
        block = run_qa("parcels", [parcel(1, geom=BOWTIE)], promote=True)

        assert (warn.decision, warn.promoted, warn.to_dict()["promotable"]) == (Outcome.WARN, True, True)
        assert (block.decision, block.promoted, block.to_dict()["promotable"]) == (Outcome.BLOCK, False, False)

    def test_persisted_rows_keep_both_outcomes(self, conn, run_qa):
        report = run_qa("parcels", [parcel(1, soil_type=None), parcel(2, geom=BOWTIE)])

        rows = dict(conn.execute(
            "SELECT check_id, outcome FROM qa.check_result WHERE run_id = %s", (report.run_id,)
        ).fetchall())
        assert rows["optional_fields"] == "WARN"
        assert rows["geometry"] == "BLOCK"
        assert conn.execute("SELECT decision FROM qa.run WHERE run_id = %s", (report.run_id,)).fetchone()[0] == "BLOCK"


class TestMissingOptionalSoilAttributeWarnsButDoesNotBlock:
    def test_missing_soil_type_warns(self, run_qa):
        report = run_qa("parcels", [parcel(1), parcel(2, soil_type=None), parcel(3, soil_type="  ")])

        assert report.decision is Outcome.WARN
        result = report.result("optional_fields")
        assert result.outcome is Outcome.WARN
        assert result.violation_count == 2
        assert result.details["coverage"]["soil_type"] == {"unknown": 2, "known": 1, "unknown_ratio": 0.6667}

    def test_missing_soil_attributes_on_peatland_warn(self, run_qa):
        report = run_qa("peatland", [peat(1, peat_depth_cm=None, soil_organic_carbon_pct=None)])

        assert report.decision is Outcome.WARN
        assert report.result("optional_fields").issue_counts == {"missing_optional_value": 2}

    def test_unknown_stays_null_after_promotion(self, conn, run_qa):
        report = run_qa("parcels", [parcel(1, soil_type=None)], promote=True)

        assert report.promoted
        assert conn.execute("SELECT soil_type FROM curated.parcels WHERE parcel_id = 'P-001'").fetchone() == (None,)

    def test_even_all_rows_missing_optional_only_warns(self, run_qa):
        report = run_qa("parcels", [parcel(n, soil_type=None) for n in range(1, 6)])

        assert report.decision is Outcome.WARN


MALFORMED = {
    "self_intersection": (BOWTIE, "invalid_geometry"),
    "empty": ("SRID=25832;POLYGON EMPTY", "empty_geometry"),
    "wrong_srid": ("SRID=4326;POLYGON((8.3 52.5,8.301 52.5,8.301 52.501,8.3 52.501,8.3 52.5))", "wrong_srid"),
    "wrong_type": (f"SRID=25832;LINESTRING({X0} {Y0},{X0 + 100} {Y0 + 100})", "wrong_geometry_type"),
    "missing": (None, "missing_geometry"),
    "overlapping_multipolygon": (
        f"SRID=25832;MULTIPOLYGON((({X0} {Y0},{X0 + 200} {Y0},{X0 + 200} {Y0 + 200},{X0} {Y0 + 200},{X0} {Y0})),"
        f"(({X0 + 100} {Y0 + 100},{X0 + 300} {Y0 + 100},{X0 + 300} {Y0 + 300},{X0 + 100} {Y0 + 300},{X0 + 100} {Y0 + 100})))",
        "invalid_geometry",
    ),
}


class TestMalformedParcelGeometryBlocksPromotion:
    @pytest.mark.parametrize("geom, issue", MALFORMED.values(), ids=MALFORMED.keys())
    def test_malformed_geometry_blocks(self, run_qa, geom, issue):
        report = run_qa("parcels", [parcel(1), parcel(2, geom=geom)], promote=True)

        assert report.decision is Outcome.BLOCK
        assert not report.promoted
        geometry = report.result("geometry")
        assert geometry.outcome is Outcome.BLOCK
        assert issue in geometry.issue_counts
        assert geometry.evidence[0]["key"] == "P-002"

    def test_invalid_geometry_evidence_names_the_defect(self, run_qa):
        report = run_qa("parcels", [parcel(1, geom=BOWTIE)])

        assert report.result("geometry").evidence[0]["reason"].startswith("Self-intersection")

    def test_blocked_batch_leaves_curated_untouched(self, conn, run_qa):
        run_qa("parcels", [parcel(1), parcel(2)], promote=True)
        before = conn.execute("SELECT parcel_id, qa_run_id FROM curated.parcels ORDER BY 1").fetchall()

        blocked = run_qa("parcels", [parcel(1), parcel(3, geom=BOWTIE)], promote=True)

        assert not blocked.promoted
        assert conn.execute("SELECT parcel_id, qa_run_id FROM curated.parcels ORDER BY 1").fetchall() == before

    def test_one_bad_row_is_not_reported_again_by_dependent_checks(self, run_qa):
        report = run_qa("parcels", [parcel(1, geom=BOWTIE, area_m2=1)])

        assert report.result("declared_area").outcome is Outcome.PASS
        assert report.result("declared_area").details["not_evaluated_bad_geometry"] == 1
        assert report.result("country_scope").details["containment_not_evaluated"] == 1


class TestDuplicateKeysBlockOrQuarantineDeterministically:
    def test_duplicate_parcel_key_blocks(self, run_qa):
        rows = [parcel(1), parcel(2), parcel(2, geom=square(X0 + 5000, Y0))]
        report = run_qa("parcels", rows, promote=True)

        assert report.decision is Outcome.BLOCK
        assert not report.promoted
        result = report.result("key_uniqueness")
        assert result.evidence == [
            {"issue": "duplicate_key", "severity": "BLOCK", "country_code": "DE", "key": "P-002", "rows": 2}
        ]

    def test_same_key_in_different_countries_is_not_a_duplicate(self, run_qa):
        report = run_qa("parcels", [parcel(1), parcel(1, country_code="NL", region_code="NL-GR")])

        assert report.result("key_uniqueness").outcome is Outcome.PASS

    def test_missing_key_blocks(self, run_qa):
        report = run_qa("parcels", [parcel(1), parcel(2, parcel_id=None)])

        assert report.result("key_uniqueness").issue_counts == {"missing_key": 1}
        assert report.decision is Outcome.BLOCK

    def _screening_batch(self):
        base = [site(n, parcel_n=n) for n in range(1, 9)]
        dup_a = site(9, parcel_n=9, eligible=4000, suitability="high")
        dup_b = site(9, parcel_n=9, eligible=3000, suitability="low", geom=square(X0 + 1800, Y0, 50, 100))
        return base, dup_a, dup_b

    def _seed_references(self, run_qa):
        assert run_qa("parcels", [parcel(n) for n in range(1, 10)], promote=True).promoted

    def test_screening_quarantines_every_member_of_a_duplicate_group(self, conn, run_qa):
        self._seed_references(run_qa)
        base, dup_a, dup_b = self._screening_batch()

        report = run_qa("screening", [*base, dup_a, dup_b], promote=True)

        assert report.decision is Outcome.WARN
        assert report.promoted
        assert [(q.country_code, q.key) for q in report.quarantine] == [("DE", "SC-009")]
        promoted = [r[0] for r in conn.execute("SELECT site_id FROM curated.screening ORDER BY 1")]
        assert promoted == [f"SC-{n:03d}" for n in range(1, 9)]
        held = conn.execute(
            "SELECT record_key, row_data->>'suitability' FROM qa.quarantine WHERE run_id = %s ORDER BY 2",
            (report.run_id,),
        ).fetchall()
        assert held == [("SC-009", "high"), ("SC-009", "low")]

    def test_quarantine_outcome_does_not_depend_on_load_order(self, run_qa):
        self._seed_references(run_qa)
        base, dup_a, dup_b = self._screening_batch()

        first = run_qa("screening", [dup_a, *base, dup_b]).to_dict()
        second = run_qa("screening", [dup_b, *reversed(base), dup_a]).to_dict()

        assert first["dataset_fingerprint"] == second["dataset_fingerprint"]
        assert first["quarantined_rows"] == second["quarantined_rows"]
        assert first["checks"] == second["checks"]

    def test_quarantine_beyond_limit_blocks(self, run_qa):
        self._seed_references(run_qa)
        rows = [site(1, parcel_n=1), site(1, parcel_n=1, suitability="low"), site(2, parcel_n=2)]

        report = run_qa("screening", rows, promote=True)

        assert report.decision is Outcome.BLOCK
        assert not report.promoted
        assert "quarantine_limit_exceeded" in report.result("key_uniqueness").issue_counts

    def test_blocked_batch_records_no_partial_quarantine(self, conn, run_qa):
        self._seed_references(run_qa)
        rows = [site(1, parcel_n=1), site(1, parcel_n=1, suitability="low"), site(2, parcel_n=2)]

        report = run_qa("screening", rows, promote=True)

        assert report.quarantine == []
        assert report.result("key_uniqueness").evidence[0]["key"] == "SC-001"
        assert conn.execute("SELECT count(*) FROM qa.quarantine").fetchone()[0] == 0
