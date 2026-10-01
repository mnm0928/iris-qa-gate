from __future__ import annotations

import os
from datetime import date
from typing import Any

import psycopg
import pytest
from psycopg import sql

from iris_qa import db, engine
from iris_qa.profile import load_profiles

TEST_DSN = os.environ.get("IRIS_QA_TEST_DSN", "postgresql://iris:iris@localhost:55432/iris_test")
AS_OF = date(2026, 9, 30)

X0, Y0 = 520000, 5820000


def square(x: float = X0, y: float = Y0, w: float = 100, h: float = 100, srid: int = 25832) -> str:
    return f"SRID={srid};POLYGON(({x} {y},{x + w} {y},{x + w} {y + h},{x} {y + h},{x} {y}))"


def point(x: float = X0, y: float = Y0) -> str:
    return f"SRID=25832;POINT({x} {y})"


BOWTIE = f"SRID=25832;POLYGON(({X0} {Y0},{X0 + 100} {Y0 + 100},{X0 + 100} {Y0},{X0} {Y0 + 100},{X0} {Y0}))"


def parcel(n: int = 1, **overrides: Any) -> dict[str, Any]:
    row = {
        "parcel_id": f"P-{n:03d}", "country_code": "DE", "region_code": "DE-NI", "municipality": "Diepholz",
        "land_use": "arable", "area_m2": 10000, "soil_type": "loam", "source_date": "2026-01-15",
        "geom": square(X0 + 200 * n),
    }
    return {**row, **overrides}


def substation(n: int = 1, **overrides: Any) -> dict[str, Any]:
    row = {
        "substation_id": f"S-{n:02d}", "country_code": "DE", "region_code": "DE-NI", "name": f"UW {n}",
        "operator": "TenneT", "voltage_kv": 110, "capacity_mva": 63, "source_date": "2026-06-01",
        "geom": point(X0 + 1000 * n, Y0 + 2000),
    }
    return {**row, **overrides}


def peat(n: int = 1, **overrides: Any) -> dict[str, Any]:
    row = {
        "peat_id": f"PT-{n:02d}", "country_code": "DE", "region_code": "DE-NI", "peat_class": "bog",
        "peat_depth_cm": 150, "soil_organic_carbon_pct": 40, "source_date": "2020-05-01",
        "geom": square(X0 + 1000 * n, Y0 + 5000, 300, 300),
    }
    return {**row, **overrides}


def site(n: int = 1, parcel_n: int = 1, eligible: float = 5000, **overrides: Any) -> dict[str, Any]:
    row = {
        "site_id": f"SC-{n:03d}", "country_code": "DE", "region_code": "DE-NI", "parcel_id": f"P-{parcel_n:03d}",
        "suitability": "high", "eligible_area_m2": eligible, "eco_point_factor": 8,
        "eco_points_estimate": eligible * 8, "nearest_substation_id": None, "source_date": "2026-08-15",
        "geom": square(X0 + 200 * parcel_n, Y0),
    }
    return {**row, **overrides}


@pytest.fixture(scope="session")
def database() -> str:
    base = psycopg.conninfo.conninfo_to_dict(TEST_DSN)
    name = base["dbname"]
    admin = psycopg.conninfo.make_conninfo(TEST_DSN, dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    with db.connect(TEST_DSN) as conn:
        db.migrate(conn)
    return TEST_DSN


@pytest.fixture
def conn(database: str):
    with db.connect(database) as c:
        c.execute(
            "TRUNCATE staging.parcels, staging.substations, staging.peatland, staging.screening, "
            "curated.parcels, curated.substations, curated.peatland, curated.screening, "
            "qa.run, qa.check_result, qa.quarantine CASCADE"
        )
        yield c


@pytest.fixture(scope="session")
def profiles():
    return load_profiles()


def stage(conn: psycopg.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    conn.execute(sql.SQL("TRUNCATE {}").format(sql.Identifier(*table.split("."))))
    for row in rows:
        conn.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(*table.split(".")),
                sql.SQL(", ").join(sql.Identifier(k) for k in row),
                sql.SQL(", ").join(sql.Placeholder() for _ in row),
            ),
            list(row.values()),
        )


@pytest.fixture
def run_qa(conn, profiles):
    def _run(dataset: str, rows: list[dict[str, Any]] | None = None, *, promote: bool = False, profile=None):
        profile = profile or profiles[dataset]
        if rows is not None:
            stage(conn, profile.dataset.staging_table, rows)
        return engine.run(conn, profile, AS_OF, promote=promote)

    return _run
