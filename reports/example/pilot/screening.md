# QA report · `screening` · 🟡 WARN

| | |
|---|---|
| Run | `10f05ae7-82cc-4ab5-aa2b-133f4f93cd0e` |
| As of | 2026-09-30 |
| Rows | 11 |
| Dataset fingerprint | `90e27784d0b597197a799676857a63cf` |
| Profile | `screening` (sha256 `143f2e34e5aa…`) |
| Decision | **WARN** — promotable; warnings are reported, unknowns stay NULL |
| Promoted | yes |
| Quarantined keys | 1 |

## Checks

| # | Check | Impl | Outcome | Violations | Summary |
|---|---|---|---|---|---|
| 1 | `required_fields` | python | 🟢 PASS | 0 | no violations |
| 2 | `optional_fields` | python | 🟡 WARN | 1 | warn: nearest_substation_id unknown on 1/11 rows (kept NULL, not imputed) |
| 3 | `key_uniqueness` | sql | 🟡 WARN | 1 | warn: 1 duplicate_key_quarantined |
| 4 | `geometry` | sql | 🟢 PASS | 0 | no violations |
| 5 | `country_scope` | sql | 🟢 PASS | 0 | no violations |
| 6 | `duplicate_rows` | sql | 🟢 PASS | 0 | no violations |
| 7 | `parcel_reference` | sql | 🟢 PASS | 0 | no violations |
| 8 | `substation_reference` | sql | 🟢 PASS | 0 | no violations |
| 9 | `eligible_area_within_site` | python | 🟢 PASS | 0 | no violations |
| 10 | `eco_points_arithmetic` | python | 🟢 PASS | 0 | no violations |
| 11 | `suitability_domain` | python | 🟢 PASS | 0 | no violations |
| 12 | `source_date` | python | 🟢 PASS | 0 | no violations |

### 🟡 WARN `optional_fields`

warn: nearest_substation_id unknown on 1/11 rows (kept NULL, not imputed)

Issues: `missing_optional_value` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `missing_optional_value` | DE | `SC-004` | {"field": "nearest_substation_id", "value": "unknown"} |

### 🟡 WARN `key_uniqueness`

warn: 1 duplicate_key_quarantined

Issues: `duplicate_key_quarantined` × 1

| Severity | Issue | Country | Key | Evidence |
|---|---|---|---|---|
| WARN | `duplicate_key_quarantined` | DE | `SC-010` | {"rows": 2} |

## Quarantine

Withheld from promotion, all members of each group:

- `DE` / `SC-010` — duplicate_key

---

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
