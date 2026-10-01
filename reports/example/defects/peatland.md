# QA report · `peatland` · 🔴 BLOCK

| | |
|---|---|
| Run | `ee31bed1-3819-4add-b63a-034c02bd5bdf` |
| As of | 2026-09-30 |
| Rows | 5 |
| Dataset fingerprint | `140623a701b2892fdc3646a7a6ed2c63` |
| Profile | `peatland` (sha256 `793939eb9e64…`) |
| Decision | **BLOCK** — promotion blocked |
| Promoted | no |
| Quarantined keys | 0 |

## Checks

| # | Check | Impl | Outcome | Violations | Summary |
|---|---|---|---|---|---|
| 1 | `required_fields` | python | 🔴 BLOCK | 1 | block: 1 missing_required_value |
| 2 | `optional_fields` | python | 🟡 WARN | 2 | warn: peat_depth_cm unknown on 1/5 rows; soil_organic_carbon_pct unknown on 1/5 rows (kept NULL, not imputed) |
| 3 | `key_uniqueness` | sql | 🟢 PASS | 0 | no violations |
| 4 | `geometry` | sql | 🔴 BLOCK | 2 | block: 1 empty_geometry, 1 invalid_geometry |
| 5 | `country_scope` | sql | 🟢 PASS | 0 | no violations |
| 6 | `duplicate_rows` | sql | 🟢 PASS | 0 | no violations |
| 7 | `peat_class_domain` | python | 🔴 BLOCK | 1 | block: 1 value_not_allowed |
| 8 | `soil_organic_carbon_range` | python | 🔴 BLOCK | 1 | block: 1 value_out_of_range |
| 9 | `source_date` | python | 🔴 BLOCK | 1 | block: 1 missing_source_date |

### 🔴 BLOCK `required_fields`

block: 1 missing_required_value

Issues: `missing_required_value` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `missing_required_value` | DE | `PT-15` | {"field": "source_date"} |

### 🟡 WARN `optional_fields`

warn: peat_depth_cm unknown on 1/5 rows; soil_organic_carbon_pct unknown on 1/5 rows (kept NULL, not imputed)

Issues: `missing_optional_value` × 2

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `missing_optional_value` | DE | `PT-13` | {"field": "peat_depth_cm", "value": "unknown"} |
| WARN | `missing_optional_value` | DE | `PT-15` | {"field": "soil_organic_carbon_pct", "value": "unknown"} |

### 🔴 BLOCK `geometry`

block: 1 empty_geometry, 1 invalid_geometry

Issues: `empty_geometry` × 1, `invalid_geometry` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `empty_geometry` | DE | `PT-14` |  |
| BLOCK | `invalid_geometry` | DE | `PT-15` | {"reason": "Self-intersection[528200 5825100]"} |

### 🔴 BLOCK `peat_class_domain`

block: 1 value_not_allowed

Issues: `value_not_allowed` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `value_not_allowed` | DE | `PT-12` | {"column": "peat_class", "value": "swamp", "allowed": ["bog", "fen", "transitional"]} |

### 🔴 BLOCK `soil_organic_carbon_range`

block: 1 value_out_of_range

Issues: `value_out_of_range` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `value_out_of_range` | DE | `PT-13` | {"column": "soil_organic_carbon_pct", "value": 140.0, "min": 0, "max": 100} |

### 🔴 BLOCK `source_date`

block: 1 missing_source_date

Issues: `missing_source_date` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| BLOCK | `missing_source_date` | DE | `PT-15` |  |

---

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
