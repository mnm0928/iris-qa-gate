# IRIS QA Gate

A small tool that checks map data for mistakes **before** anyone is allowed to use it.


## What does it do?

Think of airport security. Data arrives, goes through a set of checks, and gets one of three results:

| Result | Meaning | Is the data allowed through? |
|---|---|---|
| **PASS** | Nothing wrong. | Yes |
| **WARN** | Small issue, e.g. an optional value is missing or the source is old. | Yes, but the issue is recorded |
| **BLOCK** | Serious issue, e.g. broken shape, duplicate ID, wrong country, wrong arithmetic. | No, nothing is promoted |

It handles four datasets: **parcels** (land plots), **substations** (power stations), **peatland** and **screening** (candidate sites with an estimated eco-point value).

Data moves through two tables:

1. **Staging**: raw data is loaded here first. It is relaxed on purpose, so bad data can be loaded and *reported* instead of crashing.
2. **Curated**: the approved data. It is strict. Data is copied here ("promoted") only if the checks allow it.

Every run is saved to the database, and can also be written out as JSON and Markdown reports.

## What you need

- Python 3.12 or newer
- Docker (runs the database)

## Quick start

```bash
# 1. Start the database (PostgreSQL 16 + PostGIS) on localhost:55432
docker compose up -d --wait

# 2. Create a Python environment and install the project
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. Create the database tables
iris-qa migrate

# 4. Try the clean sample data: should pass with warnings and be promoted
iris-qa load fixtures/pilot
iris-qa run --as-of 2026-09-30 --promote --out reports/pilot

# 5. Try the deliberately broken sample data: everything should be blocked
iris-qa load fixtures/defects
iris-qa run --as-of 2026-09-30 --promote --out reports/defects    # exits with code 2

# 6. Run the automated tests
pytest
```

Notes:

- `--as-of` sets the date used for date checks (future or too-old source dates). It is optional and defaults to today.
  I pin it so the results are the same every time the project is run.
- On Apple Silicon Macs the database image runs under emulation. It is a bit slower but fine for this small data.


## Commands

| Command | What it does |
|---|---|
| `iris-qa migrate` | Creates the database tables. Safe to run again. |
| `iris-qa profiles` | Lists each dataset and the checks it runs. |
| `iris-qa load FOLDER` | Loads the CSV files from a folder into the staging tables (replacing what was there). |
| `iris-qa run` | Runs the checks. Add `--promote` to copy passing data to curated, `--out FOLDER` to write reports, `--strict` to treat warnings as failures, or a dataset name (e.g. `parcels`) to run just one. |
| `iris-qa show RUN_ID` | Prints a saved run again. |
| `iris-qa history` | Lists recent runs. |
| `pytest` | Runs the tests. |

Exit codes: `0` = nothing blocked, `1` = warnings (only with `--strict`), `2` = something was blocked, `3` = bad command or profile.

## What you should see

| Dataset | Clean sample (`pilot`) | Broken sample (`defects`) |
|---|---|---|
| parcels | WARN: 2 parcels have no soil type (allowed) | BLOCK |
| peatland | WARN: some depth/carbon values missing | BLOCK |
| substations | PASS | BLOCK |
| screening | WARN: one duplicated site set aside (quarantined), the rest promoted | BLOCK |

Example reports from both runs are in [`reports/example/pilot/summary.md`](reports/example/pilot/summary.md) and
[`reports/example/defects/summary.md`](reports/example/defects/summary.md).

## The rules behind the results

- **Missing optional data only warns.** It is left empty (`NULL`) and shown as "unknown". I never fill in or guess missing values.
  If a field is important enough to stop a launch, it should be *required*, not optional.
- **Broken geometry blocks.** A parcel whose outline crosses itself, has the wrong shape type, the wrong coordinate system, or lies outside the allowed region cannot be promoted.
- **Duplicate IDs are handled the same way every time.**
  Parcels, substations and peatland: a duplicate ID blocks.
  Screening: **every** row with a duplicated ID is *quarantined* (set aside and saved for review). I do not "keep the first one", because that would depend on the order of the rows.
  If more than 25% of the rows would be quarantined, the run blocks instead.
- **Blocks and warnings are separate.** Every problem found carries its own severity, so a report shows exactly which rows caused a block.
- **A check that crashes counts as BLOCK.** When in doubt, the data does not go through.
- **IDs are scoped by country.** The same `parcel_id` in two countries is not a duplicate.
- **Results are reproducible.** Rows are processed in a fixed order, and each run records a fingerprint of the data and of the profile used.

## How it works

```
profiles/*.toml  →  which checks to run for each dataset
        ↓
staging table  →  run the checks  →  save results (database + optional report files)
                          ↓
              nothing blocked?  →  yes: copy to curated table
                                   no:  stop, curated table is untouched
```

### Project layout

| Folder / file | What is in it |
|---|---|
| `fixtures/` | Small made-up CSV files: `pilot/` (mostly clean) and `defects/` (planted mistakes) |
| `migrations/` | SQL scripts that create the database tables |
| `profiles/` | One settings file (`.toml`) per dataset, listing its checks |
| `src/iris_qa/engine.py` | Runs the checks, saves the results, promotes data |
| `src/iris_qa/checks/sql_checks.py` | Checks done inside the database with SQL/PostGIS |
| `src/iris_qa/checks/python_checks.py` | Checks done in Python |
| `src/iris_qa/checks/base.py` | The common template every check follows |
| `src/iris_qa/profile.py` | Reads and validates the profile files |
| `src/iris_qa/report.py` | Writes the JSON and Markdown reports |
| `src/iris_qa/cli.py` | The `iris-qa` commands |
| `tests/` | The automated tests |
| `reports/example/` | Example reports from the two sample runs |

### The checks

SQL checks (run in PostGIS):

| Check | Looks for |
|---|---|
| `key_uniqueness` | Missing or repeated IDs |
| `geometry` | Empty, invalid, wrong-type or wrong-coordinate-system shapes |
| `country_scope` | Wrong country or region, shapes outside the allowed area |
| `duplicate_rows` | Different IDs describing the same shape |
| `reference_integrity` | IDs that point to something that doesn't exist |

Python checks:

| Check | Looks for |
|---|---|
| `required_fields` | Empty values in required columns |
| `optional_fields` | Empty optional values (warning only) |
| `source_date` | Missing, invalid or future dates (block); old dates (warning) |
| `declared_area` | Stated area that does not match the shape's real area |
| `product_consistency` | Eco-points that are not area × 8 |
| `domain` | Values outside the allowed list or range |

### Profiles

A profile is a short settings file. This is a shortened version of `profiles/parcels.toml`:

```toml
[dataset]
name = "parcels"
key = "parcel_id"
countries = ["DE"]

[[checks]]
type = "required_fields"
fields = ["parcel_id", "country_code", "area_m2", "geom"]

[[checks]]
type = "optional_fields"
fields = ["soil_type"]

[[checks]]
type = "source_date"
max_age_days = 1095
```

A profile can make an issue stricter, for example making old source dates block. It cannot make an optional-field problem block:

```toml
[[checks]]
type = "source_date"
max_age_days = 180
severity = { stale_source_date = "block" }
```

Profiles are validated when loaded, so typos and bad settings fail early with a clear error.

## Extending it

- **New dataset:** add its tables in a new migration and a `profiles/<name>.toml`. No Python code is needed.
- **New check:** write a class that follows the template in `checks/base.py` and mark it `@register`. Any profile can then use it.
- **New country or region:** add a row to `ref.region` and list it in the profile.

## Assumptions and simplifications


- **Region border:** I used a plain rectangle instead of the real Niedersachsen border. A real system would load the official border.
- **Loading data:** each load wipes the old staging data. A real system would keep every upload and record where it came from.
- **Promotion:** approved data is replaced as a whole each time. A real system would update only what changed and keep older versions.
- **Duplicate points:** found by rounding coordinates, so very close points could be missed. A real system would measure the distance between them.
- **Area:** measured as if the map were flat, which is fine for a small region. A real system would use a method that handles curvature.
- **Eco-point factor (8):** fixed in the profile. A real system would keep it in a versioned table.
- **Report examples:** only the first 25 problems per check are listed (the counts are complete). A real system would store them all.
- **Memory:** some checks load all rows into memory. A real system would process big datasets in pieces.
- **"Too old" limits:** these are placeholder numbers. They should come from the data owners.

---

*Preliminary prospecting material. Figures, eco-point estimates and site suitability are indicative and based on available source data and commercial screening assumptions. The 8 eco-points/m² factor is the current commercial baseline, not certified compensation. Ownership, planning, grid capacity, environmental eligibility and transferability remain subject to project-specific verification. No permit, reservation or construction readiness is represented.*
