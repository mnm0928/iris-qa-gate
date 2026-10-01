# QA report · `parcels` · 🔴 BLOCK

| | |
|---|---|
| Run | `91b04f13-3ba5-41ae-9f15-1620bc03103c` |
| As of | 2026-09-30 |
| Rows | 15 |
| Dataset fingerprint | `ce026549735923a0e111560a45d93bf2` |
| Profile | `parcels` (sha256 `144fbfc2c614…`) |
| Decision | **BLOCK** — promotion blocked |
| Promoted | no |
| Quarantined keys | 0 |

## Checks

| # | Check | Impl | Outcome | Violations | Summary |
|---|---|---|---|---|---|
| 1 | `required_fields` | python | 🔴 BLOCK | 1 | block: 1 missing_required_value |
| 2 | `optional_fields` | python | 🟡 WARN | 2 | warn: soil_type unknown on 2/15 rows (kept NULL, not imputed) |
| 3 | `key_uniqueness` | sql | 🔴 BLOCK | 1 | block: 1 duplicate_key |
| 4 | `geometry` | sql | 🔴 BLOCK | 3 | block: 1 invalid_geometry, 1 wrong_geometry_type, 1 wrong_srid |
| 5 | `country_scope` | sql | 🔴 BLOCK | 2 | block: 1 country_out_of_scope, 1 geometry_outside_region |
| 6 | `duplicate_rows` | sql | 🔴 BLOCK | 1 | block: 1 duplicate_record |
| 7 | `declared_area` | python | 🔴 BLOCK | 1 | block: 1 area_mismatch |
| 8 | `source_date` | python | 🔴 BLOCK | 3 | block: 1 future_source_date, 1 stale_source_date, 1 unparseable_source_date |
| 9 | `land_use_domain` | python | 🔴 BLOCK | 1 | block: 1 value_not_allowed |

### 🔴 BLOCK `required_fields`

block: 1 missing_required_value

Issues: `missing_required_value` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `missing_required_value` | DE | `P-110` | {"field": "municipality"} |

### 🟡 WARN `optional_fields`

warn: soil_type unknown on 2/15 rows (kept NULL, not imputed)

Issues: `missing_optional_value` × 2

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `missing_optional_value` | DE | `P-103` | {"field": "soil_type", "value": "unknown"} |
| WARN | `missing_optional_value` | DE | `P-114` | {"field": "soil_type", "value": "unknown"} |

### 🔴 BLOCK `key_uniqueness`

block: 1 duplicate_key

Issues: `duplicate_key` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `duplicate_key` | DE | `P-104` | {"rows": 2} |

### 🔴 BLOCK `geometry`

block: 1 invalid_geometry, 1 wrong_geometry_type, 1 wrong_srid

Issues: `invalid_geometry` × 1, `wrong_geometry_type` × 1, `wrong_srid` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `invalid_geometry` | DE | `P-102` | {"reason": "Self-intersection[525250 5820050]"} |
| BLOCK | `wrong_srid` | DE | `P-109` | {"srid": 4326, "expected": 25832} |
| BLOCK | `wrong_geometry_type` | DE | `P-113` | {"geometry_type": "LINESTRING", "expected": ["POLYGON", "MULTIPOLYGON"]} |

### 🔴 BLOCK `country_scope`

block: 1 country_out_of_scope, 1 geometry_outside_region

Issues: `country_out_of_scope` × 1, `geometry_outside_region` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `geometry_outside_region` | DE | `P-107` | {"region_code": "DE-NI", "distance_to_region_m": 100000.0} |
| BLOCK | `country_out_of_scope` | NL | `P-106` | {"region_code": "NL-GR"} |

### 🔴 BLOCK `duplicate_rows`

block: 1 duplicate_record

Issues: `duplicate_record` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `duplicate_record` | DE | `P-101` | {"duplicate_keys": ["P-101", "P-108"], "rows": 2} |

### 🔴 BLOCK `declared_area`

block: 1 area_mismatch

Issues: `area_mismatch` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `area_mismatch` | DE | `P-105` | {"deviation": 0.25, "declared_m2": 12500.0, "geometry_m2": 10000.0} |

### 🔴 BLOCK `source_date`

block: 1 future_source_date, 1 stale_source_date, 1 unparseable_source_date

Issues: `future_source_date` × 1, `stale_source_date` × 1, `unparseable_source_date` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `future_source_date` | DE | `P-111` | {"value": "2027-01-01", "as_of": "2026-09-30"} |
| BLOCK | `unparseable_source_date` | DE | `P-112` | {"value": "2025-13-45"} |
| WARN | `stale_source_date` | DE | `P-114` | {"value": "2021-01-15", "age_days": 2084, "max_age_days": 1095} |

### 🔴 BLOCK `land_use_domain`

block: 1 value_not_allowed

Issues: `value_not_allowed` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `value_not_allowed` | DE | `P-112` | {"column": "land_use", "value": "parking", "allowed": ["arable", "grassland", "forest", "wetland", "fallow"]} |

---

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
