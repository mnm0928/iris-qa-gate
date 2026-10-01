CREATE TABLE staging.parcels (
    parcel_id    text,
    country_code text,
    region_code  text,
    municipality text,
    land_use     text,
    area_m2      numeric,
    soil_type    text,
    source_date  text,
    geom         geometry
);

CREATE TABLE staging.substations (
    substation_id text,
    country_code  text,
    region_code   text,
    name          text,
    operator      text,
    voltage_kv    numeric,
    capacity_mva  numeric,
    source_date   text,
    geom          geometry
);

CREATE TABLE staging.peatland (
    peat_id                  text,
    country_code             text,
    region_code              text,
    peat_class               text,
    peat_depth_cm            numeric,
    soil_organic_carbon_pct  numeric,
    source_date              text,
    geom                     geometry
);

CREATE TABLE staging.screening (
    site_id               text,
    country_code          text,
    region_code           text,
    parcel_id             text,
    suitability           text,
    eligible_area_m2      numeric,
    eco_point_factor      numeric,
    eco_points_estimate   numeric,
    nearest_substation_id text,
    source_date           text,
    geom                  geometry
);
