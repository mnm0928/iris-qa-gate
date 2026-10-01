"""End-to-end regression over the committed fixture scenarios, through the CLI."""

from __future__ import annotations

import json
from pathlib import Path

from iris_qa.cli import EXIT_BLOCK, EXIT_OK, main

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def cli(database: str, *args: str) -> int:
    return main(["--dsn", database, *args])


def decisions(directory: Path) -> dict[str, str]:
    return {p.stem: json.loads(p.read_text())["decision"] for p in sorted(directory.glob("*.json"))}


def test_pilot_scenario_promotes_with_warnings(conn, database, tmp_path):
    assert cli(database, "load", str(FIXTURES / "pilot")) == EXIT_OK
    assert cli(database, "run", "--as-of", "2026-09-30", "--promote", "--out", str(tmp_path)) == EXIT_OK

    assert decisions(tmp_path) == {"parcels": "WARN", "peatland": "WARN", "screening": "WARN", "substations": "PASS"}
    screening = json.loads((tmp_path / "screening.json").read_text())
    assert screening["promoted"] and screening["quarantined_rows"] == [
        {"country_code": "DE", "key": "SC-010", "reason": "duplicate_key"}
    ]
    assert conn.execute("SELECT count(*) FROM curated.screening").fetchone()[0] == 9
    assert (tmp_path / "summary.md").exists()


def test_defects_scenario_blocks_every_dataset(conn, database, tmp_path):
    cli(database, "load", str(FIXTURES / "pilot"))
    cli(database, "run", "--as-of", "2026-09-30", "--promote")
    curated_before = conn.execute("SELECT count(*) FROM curated.parcels").fetchone()[0]

    assert cli(database, "load", str(FIXTURES / "defects")) == EXIT_OK
    assert cli(database, "run", "--as-of", "2026-09-30", "--promote", "--out", str(tmp_path)) == EXIT_BLOCK

    assert set(decisions(tmp_path).values()) == {"BLOCK"}
    assert conn.execute("SELECT count(*) FROM curated.parcels").fetchone()[0] == curated_before
    parcels = json.loads((tmp_path / "parcels.json").read_text())
    assert parcels["warning_checks"] == ["optional_fields"]
    assert "geometry" in parcels["blocking_checks"]
