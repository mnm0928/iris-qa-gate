# QA report · `substations` · 🔴 BLOCK

| | |
|---|---|
| Run | `806bc1c1-06b1-4ec1-b953-beed9a8d5bbc` |
| As of | 2026-09-30 |
| Rows | 6 |
| Dataset fingerprint | `a25acb0283ad332c114c065c4b187779` |
| Profile | `substations` (sha256 `31a9ce6576cb…`) |
| Decision | **BLOCK** — promotion blocked |
| Promoted | no |
| Quarantined keys | 0 |

## Checks

| # | Check | Impl | Outcome | Violations | Summary |
|---|---|---|---|---|---|
| 1 | `required_fields` | python | 🔴 BLOCK | 1 | block: 1 missing_required_value |
| 2 | `optional_fields` | python | 🟡 WARN | 2 | warn: operator unknown on 1/6 rows; capacity_mva unknown on 1/6 rows (kept NULL, not imputed) |
| 3 | `key_uniqueness` | sql | 🟢 PASS | 0 | no violations |
| 4 | `geometry` | sql | 🔴 BLOCK | 1 | block: 1 wrong_geometry_type |
| 5 | `country_scope` | sql | 🔴 BLOCK | 1 | block: 1 missing_country_code |
| 6 | `duplicate_rows` | sql | 🔴 BLOCK | 1 | block: 1 duplicate_record |
| 7 | `voltage_range` | python | 🔴 BLOCK | 1 | block: 1 value_out_of_range |
| 8 | `source_date` | python | 🟡 WARN | 1 | warn: 1 stale_source_date |

### 🔴 BLOCK `required_fields`

block: 1 missing_required_value

Issues: `missing_required_value` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `missing_required_value` | ∅ | `S-12` | {"field": "country_code"} |

### 🟡 WARN `optional_fields`

warn: operator unknown on 1/6 rows; capacity_mva unknown on 1/6 rows (kept NULL, not imputed)

Issues: `missing_optional_value` × 2

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `missing_optional_value` | ∅ | `S-12` | {"field": "operator", "value": "unknown"} |
| WARN | `missing_optional_value` | ∅ | `S-12` | {"field": "capacity_mva", "value": "unknown"} |

### 🔴 BLOCK `geometry`

block: 1 wrong_geometry_type

Issues: `wrong_geometry_type` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `wrong_geometry_type` | DE | `S-16` | {"geometry_type": "POLYGON", "expected": ["POINT"]} |

### 🔴 BLOCK `country_scope`

block: 1 missing_country_code

Issues: `missing_country_code` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `missing_country_code` | ∅ | `S-12` | {"region_code": "DE-NI"} |

### 🔴 BLOCK `duplicate_rows`

block: 1 duplicate_record

Issues: `duplicate_record` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `duplicate_record` | DE | `S-11` | {"duplicate_keys": ["S-11", "S-13"], "rows": 2} |

### 🔴 BLOCK `voltage_range`

block: 1 value_out_of_range

Issues: `value_out_of_range` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `value_out_of_range` | DE | `S-14` | {"column": "voltage_kv", "value": 5000.0, "min": 1, "max": 1000} |

### 🟡 WARN `source_date`

warn: 1 stale_source_date

Issues: `stale_source_date` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `stale_source_date` | DE | `S-15` | {"value": "2023-02-01", "age_days": 1337, "max_age_days": 365} |

---

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
