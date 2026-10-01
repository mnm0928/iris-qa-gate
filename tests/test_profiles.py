"""Profile loading and severity semantics; no database required."""

from __future__ import annotations

import pytest

from iris_qa.checks import REGISTRY, ProfileError
from iris_qa.model import Outcome
from iris_qa.profile import load_profile, load_profiles

MINIMAL = """
[dataset]
name = "{name}"
staging_table = "staging.parcels"
curated_table = "curated.parcels"
key = "parcel_id"
countries = ["DE"]
regions = ["DE-NI"]
{extra_dataset}

[geometry]
srid = 25832
types = ["POLYGON"]

{checks}
"""


def write_profile(tmp_path, checks: str, name: str = "parcels", extra_dataset: str = ""):
    path = tmp_path / f"{name}.toml"
    path.write_text(MINIMAL.format(name=name, checks=checks, extra_dataset=extra_dataset))
    return path


def test_shipped_profiles_cover_the_four_datasets_in_dependency_order():
    assert list(load_profiles()) == ["parcels", "peatland", "substations", "screening"]


@pytest.mark.parametrize("name", ["parcels", "peatland", "substations", "screening"])
def test_each_shipped_profile_mixes_sql_and_python_checks(name):
    implementations = {c.implementation for c in load_profiles()[name].checks}

    assert implementations == {"sql", "python"}


def test_registry_has_sql_and_python_implementations():
    assert {cls.implementation for cls in REGISTRY.values()} == {"sql", "python"}


def test_worst_outcome_wins():
    assert Outcome.worst([Outcome.PASS, Outcome.WARN]) is Outcome.WARN
    assert Outcome.worst([Outcome.WARN, Outcome.BLOCK, Outcome.PASS]) is Outcome.BLOCK
    assert Outcome.worst([]) is Outcome.PASS


def test_optional_fields_can_never_be_graded_blocking(tmp_path):
    path = write_profile(tmp_path, """
[[checks]]
type = "optional_fields"
fields = ["soil_type"]
severity = { missing_optional_value = "block" }
""")
    with pytest.raises(ProfileError, match="at most WARN"):
        load_profile(path)


def test_profile_may_downgrade_an_issue(tmp_path):
    path = write_profile(tmp_path, """
[[checks]]
type = "source_date"
severity = { future_source_date = "warn" }
""")
    check = load_profile(path).checks[0]

    assert check.severities["future_source_date"] is Outcome.WARN


@pytest.mark.parametrize("checks, message", [
    ('[[checks]]\ntype = "nope"', "unknown check type"),
    ('[[checks]]\ntype = "geometry"\nsrid = 4326', "unknown parameter"),
    ('[[checks]]\ntype = "domain"\ncolumn = "x"', "at least one of"),
    ('[[checks]]\ntype = "reference_integrity"\ncolumn = "x"', "missing parameter"),
    ('[[checks]]\ntype = "key_uniqueness"\non_duplicate = "keep_first"', "on_duplicate"),
    ('[[checks]]\ntype = "source_date"\nseverity = { old = "warn" }', "unknown issue"),
    ('[[checks]]\ntype = "geometry"\n[[checks]]\ntype = "geometry"', "duplicate check id"),
    ("", "no checks"),
])
def test_invalid_profiles_are_rejected_at_load_time(tmp_path, checks, message):
    with pytest.raises(ProfileError, match=message):
        load_profile(write_profile(tmp_path, checks))


def test_dependency_cycles_are_rejected(tmp_path):
    check = '[[checks]]\ntype = "geometry"'
    write_profile(tmp_path, check, name="a", extra_dataset='depends_on = ["b"]')
    write_profile(tmp_path, check, name="b", extra_dataset='depends_on = ["a"]')

    with pytest.raises(ProfileError, match="cycle"):
        load_profiles(tmp_path)
