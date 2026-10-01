# IRIS QA gate · summary

| Dataset | Decision | Rows | Blocking checks | Warning checks | Quarantined | Promoted |
|---|---|---|---|---|---|---|
| [`parcels`](parcels.md) | 🔴 BLOCK | 15 | `required_fields`, `key_uniqueness`, `geometry`, `country_scope`, `duplicate_rows`, `declared_area`, `source_date`, `land_use_domain` | `optional_fields` | 0 | no |
| [`peatland`](peatland.md) | 🔴 BLOCK | 5 | `required_fields`, `geometry`, `peat_class_domain`, `soil_organic_carbon_range`, `source_date` | `optional_fields` | 0 | no |
| [`substations`](substations.md) | 🔴 BLOCK | 6 | `required_fields`, `geometry`, `country_scope`, `duplicate_rows`, `voltage_range` | `optional_fields`, `source_date` | 0 | no |
| [`screening`](screening.md) | 🔴 BLOCK | 11 | `key_uniqueness`, `parcel_reference`, `substation_reference`, `eligible_area_within_site`, `eco_points_arithmetic`, `suitability_domain` | `source_date` | 0 | no |

> Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m2 factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.
