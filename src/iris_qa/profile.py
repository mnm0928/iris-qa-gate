from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from iris_qa.checks import REGISTRY, Check, DatasetSpec, ProfileError

DEFAULT_PROFILE_DIR = Path(__file__).resolve().parents[2] / "profiles"


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    depends_on: tuple[str, ...]
    dataset: DatasetSpec
    checks: tuple[Check, ...]
    sha256: str
    path: Path


def load_profile(path: Path) -> Profile:
    raw = path.read_bytes()
    try:
        doc = tomllib.loads(raw.decode())
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"{path.name}: {exc}") from exc

    ds = _section(doc, "dataset", path)
    geometry = _section(doc, "geometry", path)
    dataset = DatasetSpec(
        name=_req(ds, "name", path),
        staging_table=_req(ds, "staging_table", path),
        curated_table=_req(ds, "curated_table", path),
        key=_req(ds, "key", path),
        countries=tuple(_req(ds, "countries", path)),
        regions=tuple(_req(ds, "regions", path)),
        srid=int(_req(geometry, "srid", path)),
        geometry_types=tuple(t.upper() for t in _req(geometry, "types", path)),
    )

    checks: list[Check] = []
    for spec in doc.get("checks", []):
        spec = dict(spec)
        check_type = spec.pop("type", None)
        if check_type not in REGISTRY:
            raise ProfileError(f"{path.name}: unknown check type {check_type!r}; known: {sorted(REGISTRY)}")
        check_id = spec.pop("id", check_type)
        severity = spec.pop("severity", {})
        checks.append(REGISTRY[check_type](check_id, spec, severity))

    ids = [c.check_id for c in checks]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ProfileError(f"{path.name}: duplicate check id(s) {duplicates}; set an explicit 'id'")
    if not checks:
        raise ProfileError(f"{path.name}: profile defines no checks")

    return Profile(
        name=dataset.name,
        description=ds.get("description", ""),
        depends_on=tuple(ds.get("depends_on", [])),
        dataset=dataset,
        checks=tuple(checks),
        sha256=hashlib.sha256(raw).hexdigest(),
        path=path,
    )


def load_profiles(directory: Path = DEFAULT_PROFILE_DIR) -> dict[str, Profile]:
    """Profiles keyed by dataset name, in dependency order."""
    profiles = {p.name: p for p in (load_profile(path) for path in sorted(directory.glob("*.toml")))}
    ordered: dict[str, Profile] = {}

    def visit(name: str, trail: tuple[str, ...]) -> None:
        if name in ordered:
            return
        if name in trail:
            raise ProfileError(f"dependency cycle: {' -> '.join((*trail, name))}")
        if name not in profiles:
            raise ProfileError(f"{trail[-1]}: depends on unknown dataset {name!r}")
        for dep in profiles[name].depends_on:
            visit(dep, (*trail, name))
        ordered[name] = profiles[name]

    for name in sorted(profiles):
        visit(name, ())
    return ordered


def _section(doc: dict[str, Any], name: str, path: Path) -> dict[str, Any]:
    if not isinstance(doc.get(name), dict):
        raise ProfileError(f"{path.name}: missing [{name}] section")
    return doc[name]


def _req(section: dict[str, Any], key: str, path: Path) -> Any:
    if key not in section:
        raise ProfileError(f"{path.name}: missing required key {key!r}")
    return section[key]
