from __future__ import annotations

import pytest

from conftest import AS_OF, X0, Y0, parcel, peat, point, site, square, stage, substation
from iris_qa import engine
from iris_qa.model import Outcome
from iris_qa.profile import load_profile


class TestCountryScope:
    def test_country_code_outside_scope_blocks(self, run_qa):
        report = run_qa("parcels", [parcel(1, country_code="NL", region_code="NL-GR")])

        assert report.result("country_scope").issue_counts == {"country_out_of_scope": 1}

    def test_geometry_outside_declared_region_blocks(self, run_qa):
        report = run_qa("parcels", [parcel(1, geom=square(700000, Y0))])

        evidence = report.result("country_scope").evidence[0]
        assert evidence["issue"] == "geometry_outside_region"
        assert evidence["distance_to_region_m"] == 100000.0

    def test_unknown_region_blocks(self, run_qa):
        report = run_qa("parcels", [parcel(1, region_code="DE-BY")])

        assert report.result("country_scope").issue_counts == {"region_out_of_scope": 1}

    def test_missing_country_code_blocks_even_if_required_list_forgot_it(self, run_qa):
        report = run_qa("substations", [substation(1, country_code=None)])

        assert report.result("country_scope").issue_counts == {"missing_country_code": 1}


class TestDuplicateInflation:
    def test_distinct_keys_with_identical_geometry_block(self, run_qa):
        report = run_qa("parcels", [parcel(1), parcel(2, geom=parcel(1)["geom"])])

        result = report.result("duplicate_rows")
        assert result.outcome is Outcome.BLOCK
        assert result.evidence[0]["duplicate_keys"] == ["P-001", "P-002"]

    def test_vertex_order_does_not_hide_a_duplicate(self, run_qa):
        rotated = f"SRID=25832;POLYGON(({X0 + 300} {Y0},{X0 + 300} {Y0 + 100},{X0 + 200} {Y0 + 100},{X0 + 200} {Y0},{X0 + 300} {Y0}))"
        report = run_qa("parcels", [parcel(1), parcel(2, geom=rotated)])

        assert report.result("duplicate_rows").outcome is Outcome.BLOCK

    def test_substation_points_within_snap_grid_are_duplicates(self, run_qa):
        report = run_qa("substations", [substation(1), substation(2, geom=point(X0 + 1000.3, Y0 + 2000.2))])

        assert report.result("duplicate_rows").issue_counts == {"duplicate_record": 1}


class TestArithmetic:
    def test_declared_area_mismatch_blocks(self, run_qa):
        report = run_qa("parcels", [parcel(1, area_m2=10200)])

        evidence = report.result("declared_area").evidence[0]
        assert evidence["issue"] == "area_mismatch"
        assert evidence["deviation"] == 0.02

    def test_declared_area_within_tolerance_passes(self, run_qa):
        assert run_qa("parcels", [parcel(1, area_m2=10050)]).result("declared_area").outcome is Outcome.PASS

    def test_eco_points_must_equal_area_times_factor(self, run_qa):
        report = run_qa("screening", [site(1, eligible=5000, eco_points_estimate=50000)])

        evidence = report.result("eco_points_arithmetic").evidence[0]
        assert evidence["issue"] == "product_mismatch"
        assert (evidence["declared"], evidence["computed"]) == (50000.0, 40000.0)

    def test_eco_point_factor_is_pinned_to_the_commercial_baseline(self, run_qa):
        report = run_qa("screening", [site(1, eligible=5000, eco_point_factor=10, eco_points_estimate=50000)])

        assert report.result("eco_points_arithmetic").issue_counts == {"unexpected_constant": 1}

    def test_eligible_area_may_not_exceed_site_geometry(self, run_qa):
        report = run_qa("screening", [site(1, eligible=12000)])

        assert report.result("eligible_area_within_site").issue_counts == {"area_exceeds_geometry": 1}


class TestSourceDate:
    @pytest.mark.parametrize("value, issue", [
        (None, "missing_source_date"),
        ("2025-13-45", "unparseable_source_date"),
        ("20250101", "unparseable_source_date"),
        ("2027-01-01", "future_source_date"),
    ])
    def test_blocking_date_defects(self, run_qa, value, issue):
        report = run_qa("parcels", [parcel(1, source_date=value)])

        assert report.result("source_date").issue_counts == {issue: 1}
        assert report.result("source_date").outcome is Outcome.BLOCK

    def test_stale_date_only_warns(self, run_qa):
        report = run_qa("substations", [substation(1, source_date="2024-01-01")])

        assert report.result("source_date").outcome is Outcome.WARN
        assert report.decision is Outcome.WARN


class TestReferenceIntegrity:
    def test_reference_must_exist_in_curated_parcels(self, run_qa):
        run_qa("parcels", [parcel(1)], promote=True)

        report = run_qa("screening", [site(1, parcel_n=1), site(2, parcel_n=2)])

        assert [e["key"] for e in report.result("parcel_reference").evidence] == ["SC-002"]

    def test_reference_is_country_scoped(self, run_qa):
        run_qa("parcels", [parcel(1)], promote=True)

        report = run_qa("screening", [site(1, parcel_n=1, country_code="AT", region_code="AT-3")])

        assert report.result("parcel_reference").issue_counts == {"dangling_reference": 1}


class TestDomain:
    def test_value_outside_allowed_set_blocks(self, run_qa):
        assert run_qa("peatland", [peat(1, peat_class="swamp")]).result("peat_class_domain").outcome is Outcome.BLOCK

    def test_value_out_of_range_blocks(self, run_qa):
        report = run_qa("peatland", [peat(1, soil_organic_carbon_pct=140)])

        assert report.result("soil_organic_carbon_range").issue_counts == {"value_out_of_range": 1}

    def test_missing_value_is_left_to_the_field_checks(self, run_qa):
        report = run_qa("peatland", [peat(1, soil_organic_carbon_pct=None)])

        assert report.result("soil_organic_carbon_range").outcome is Outcome.PASS


class TestFailClosed:
    def test_check_that_cannot_run_blocks_and_others_still_run(self, tmp_path, run_qa, profiles):
        source = profiles["parcels"].path.read_text() + '\n[[checks]]\nid = "ghost"\ntype = "domain"\ncolumn = "no_such_column"\nmin = 0\n'
        path = tmp_path / "parcels.toml"
        path.write_text(source)

        report = run_qa("parcels", [parcel(1)], profile=load_profile(path))

        assert report.result("ghost").outcome is Outcome.BLOCK
        assert report.result("ghost").issue_counts == {"check_error": 1}
        assert report.result("geometry").outcome is Outcome.PASS
        assert report.decision is Outcome.BLOCK

    def test_missing_required_column_blocks(self, tmp_path, run_qa, profiles):
        source = profiles["parcels"].path.read_text().replace('"area_m2", "source_date"', '"area_m2", "cadastre_ref", "source_date"')
        path = tmp_path / "parcels.toml"
        path.write_text(source)

        report = run_qa("parcels", [parcel(1)], profile=load_profile(path))

        assert report.result("required_fields").evidence[0] == {
            "issue": "missing_column", "severity": "BLOCK", "country_code": None, "key": None, "field": "cadastre_ref"
        }


class TestRunRecord:
    def test_identical_input_yields_identical_report(self, run_qa):
        rows = [parcel(1), parcel(2, soil_type=None), parcel(3, area_m2=1)]
        first, second = run_qa("parcels", rows).to_dict(), run_qa("parcels", list(reversed(rows))).to_dict()

        volatile = {"run_id", "started_at", "finished_at"}
        assert {k: v for k, v in first.items() if k not in volatile} == {k: v for k, v in second.items() if k not in volatile}

    def test_run_summary_is_persisted(self, conn, run_qa):
        report = run_qa("parcels", [parcel(1)])

        summary, sha = conn.execute(
            "SELECT summary, profile_sha256 FROM qa.run WHERE run_id = %s", (report.run_id,)
        ).fetchone()
        assert summary["decision"] == "PASS"
        assert summary["dataset_fingerprint"] == report.dataset_fingerprint
        assert sha == report.profile_sha256
        count = conn.execute("SELECT count(*) FROM qa.check_result WHERE run_id = %s", (report.run_id,)).fetchone()[0]
        assert count == len(report.results)

    def test_promotion_replaces_the_country_slice(self, conn, run_qa):
        run_qa("parcels", [parcel(1), parcel(2)], promote=True)
        report = run_qa("parcels", [parcel(3)], promote=True)

        rows = conn.execute("SELECT parcel_id, qa_run_id::text FROM curated.parcels").fetchall()
        assert rows == [("P-003", report.run_id)]

    def test_evidence_is_capped_but_counts_are_complete(self, conn, profiles, run_qa):
        stage(conn, "staging.parcels", [parcel(n, soil_type=None) for n in range(1, 8)])
        report = engine.run(conn, profiles["parcels"], AS_OF, evidence_limit=3)

        result = report.result("optional_fields")
        assert (result.violation_count, len(result.evidence), result.evidence_truncated) == (7, 3, True)
        assert [e["key"] for e in result.evidence] == ["P-001", "P-002", "P-003"]
