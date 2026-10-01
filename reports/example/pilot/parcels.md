# QA report · `parcels` · 🟡 WARN

| | |
|---|---|
| Run | `bfca726f-07a9-42d8-80ff-21e97dcdbcd6` |
| As of | 2026-09-30 |
| Rows | 8 |
| Dataset fingerprint | `e43e7ab061c0cf120088987823954537` |
| Profile | `parcels` (sha256 `144fbfc2c614…`) |
| Decision | **WARN** — promotable; warnings are reported, unknowns stay NULL |
| Promoted | yes |
| Quarantined keys | 0 |

## Checks

| # | Check | Impl | Outcome | Violations | Summary |
|---|---|---|---|---|---|
| 1 | `required_fields` | python | 🟢 PASS | 0 | no violations |
| 2 | `optional_fields` | python | 🟡 WARN | 2 | warn: soil_type unknown on 2/8 rows (kept NULL, not imputed) |
| 3 | `key_uniqueness` | sql | 🟢 PASS | 0 | no violations |
| 4 | `geometry` | sql | 🟢 PASS | 0 | no violations |
| 5 | `country_scope` | sql | 🟢 PASS | 0 | no violations |
| 6 | `duplicate_rows` | sql | 🟢 PASS | 0 | no violations |
| 7 | `declared_area` | python | 🟢 PASS | 0 | no violations |
| 8 | `source_date` | python | 🟢 PASS | 0 | no violations |
| 9 | `land_use_domain` | python | 🟢 PASS | 0 | no violations |

### 🟡 WARN `optional_fields`

warn: soil_type unknown on 2/8 rows (kept NULL, not imputed)

Issues: `missing_optional_value` × 2

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `missing_optional_value` | DE | `P-003` | {"field": "soil_type", "value": "unknown"} |
| WARN | `missing_optional_value` | DE | `P-006` | {"field": "soil_type", "value": "unknown"} |

---

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
