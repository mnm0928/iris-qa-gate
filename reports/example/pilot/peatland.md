# QA report · `peatland` · 🟡 WARN

| | |
|---|---|
| Run | `71f9777a-d85e-4984-9ec5-c584da0df292` |
| As of | 2026-09-30 |
| Rows | 4 |
| Dataset fingerprint | `2a0783e08130038656715747fab3ef8f` |
| Profile | `peatland` (sha256 `793939eb9e64…`) |
| Decision | **WARN** — promotable; warnings are reported, unknowns stay NULL |
| Promoted | yes |
| Quarantined keys | 0 |

## Checks

| # | Check | Impl | Outcome | Violations | Summary |
|---|---|---|---|---|---|
| 1 | `required_fields` | python | 🟢 PASS | 0 | no violations |
| 2 | `optional_fields` | python | 🟡 WARN | 2 | warn: peat_depth_cm unknown on 1/4 rows; soil_organic_carbon_pct unknown on 1/4 rows (kept NULL, not imputed) |
| 3 | `key_uniqueness` | sql | 🟢 PASS | 0 | no violations |
| 4 | `geometry` | sql | 🟢 PASS | 0 | no violations |
| 5 | `country_scope` | sql | 🟢 PASS | 0 | no violations |
| 6 | `duplicate_rows` | sql | 🟢 PASS | 0 | no violations |
| 7 | `peat_class_domain` | python | 🟢 PASS | 0 | no violations |
| 8 | `soil_organic_carbon_range` | python | 🟢 PASS | 0 | no violations |
| 9 | `source_date` | python | 🟢 PASS | 0 | no violations |

### 🟡 WARN `optional_fields`

warn: peat_depth_cm unknown on 1/4 rows; soil_organic_carbon_pct unknown on 1/4 rows (kept NULL, not imputed)

Issues: `missing_optional_value` × 2

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `missing_optional_value` | DE | `PT-02` | {"field": "soil_organic_carbon_pct", "value": "unknown"} |
| WARN | `missing_optional_value` | DE | `PT-03` | {"field": "peat_depth_cm", "value": "unknown"} |

---

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
