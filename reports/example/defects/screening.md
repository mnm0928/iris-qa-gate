# QA report · `screening` · 🔴 BLOCK

| | |
|---|---|
| Run | `5fc7c4d8-6060-4f3d-82cf-79abc4d67f4c` |
| As of | 2026-09-30 |
| Rows | 11 |
| Dataset fingerprint | `2343a7395ab810710ac7850cc59ce386` |
| Profile | `screening` (sha256 `143f2e34e5aa…`) |
| Decision | **BLOCK** — promotion blocked |
| Promoted | no |
| Quarantined keys | 0 |

## Checks

| # | Check | Impl | Outcome | Violations | Summary |
|---|---|---|---|---|---|
| 1 | `required_fields` | python | 🟢 PASS | 0 | no violations |
| 2 | `optional_fields` | python | 🟢 PASS | 0 | no violations |
| 3 | `key_uniqueness` | sql | 🔴 BLOCK | 3 | block: 2 duplicate_key_quarantined, 1 quarantine_limit_exceeded |
| 4 | `geometry` | sql | 🟢 PASS | 0 | no violations |
| 5 | `country_scope` | sql | 🟢 PASS | 0 | no violations |
| 6 | `duplicate_rows` | sql | 🟢 PASS | 0 | no violations |
| 7 | `parcel_reference` | sql | 🔴 BLOCK | 1 | block: 1 dangling_reference |
| 8 | `substation_reference` | sql | 🔴 BLOCK | 1 | block: 1 dangling_reference |
| 9 | `eligible_area_within_site` | python | 🔴 BLOCK | 1 | block: 1 area_exceeds_geometry |
| 10 | `eco_points_arithmetic` | python | 🔴 BLOCK | 2 | block: 1 product_mismatch, 1 unexpected_constant |
| 11 | `suitability_domain` | python | 🔴 BLOCK | 1 | block: 1 value_not_allowed |
| 12 | `source_date` | python | 🟡 WARN | 1 | warn: 1 stale_source_date |

### 🔴 BLOCK `key_uniqueness`

block: 2 duplicate_key_quarantined, 1 quarantine_limit_exceeded

Issues: `duplicate_key_quarantined` × 2, `quarantine_limit_exceeded` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `duplicate_key_quarantined` | DE | `SC-108` | {"rows": 2} |
| WARN | `duplicate_key_quarantined` | DE | `SC-109` | {"rows": 2} |
| BLOCK | `quarantine_limit_exceeded` | ∅ | ∅ | {"quarantined_rows": 4, "ratio": 0.3636, "limit": 0.25} |

### 🔴 BLOCK `parcel_reference`

block: 1 dangling_reference

Issues: `dangling_reference` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `dangling_reference` | DE | `SC-105` | {"column": "parcel_id", "value": "P-999", "ref_table": "curated.parcels"} |

### 🔴 BLOCK `substation_reference`

block: 1 dangling_reference

Issues: `dangling_reference` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `dangling_reference` | DE | `SC-105` | {"column": "nearest_substation_id", "value": "S-99", "ref_table": "curated.substations"} |

### 🔴 BLOCK `eligible_area_within_site`

block: 1 area_exceeds_geometry

Issues: `area_exceeds_geometry` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `area_exceeds_geometry` | DE | `SC-104` | {"declared_m2": 20000.0, "geometry_m2": 13000.0} |

### 🔴 BLOCK `eco_points_arithmetic`

block: 1 product_mismatch, 1 unexpected_constant

Issues: `product_mismatch` × 1, `unexpected_constant` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `product_mismatch` | DE | `SC-102` | {"formula": "eco_points_estimate = eligible_area_m2 * eco_point_factor", "declared": 50000.0, "computed": 64000.0, "inputs": {"eligible_area_m2": 8000.0, "eco_point_factor": 8.0}} |
| BLOCK | `unexpected_constant` | DE | `SC-103` | {"column": "eco_point_factor", "value": 10.0, "expected": 8} |

### 🔴 BLOCK `suitability_domain`

block: 1 value_not_allowed

Issues: `value_not_allowed` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `value_not_allowed` | DE | `SC-106` | {"column": "suitability", "value": "sure", "allowed": ["high", "medium", "low", "excluded"]} |

### 🟡 WARN `source_date`

warn: 1 stale_source_date

Issues: `stale_source_date` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `stale_source_date` | DE | `SC-107` | {"value": "2025-11-01", "age_days": 333, "max_age_days": 180} |

---

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
