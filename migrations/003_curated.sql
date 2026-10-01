CREATE TABLE curated.parcels (
    parcel_id    text NOT NULL,
    country_code text NOT NULL,
    region_code  text NOT NULL,
    municipality text NOT NULL,
    land_use     text NOT NULL,
    area_m2      numeric NOT NULL CHECK (area_m2 > 0),
    soil_type    text,
    source_date  date NOT NULL,
    geom         geometry(Geometry, 25832) NOT NULL
                 CHECK (ST_IsValid(geom) AND GeometryType(geom) IN ('POLYGON', 'MULTIPOLYGON')),
    qa_run_id    uuid NOT NULL,
    PRIMARY KEY (country_code, parcel_id)
);

CREATE TABLE curated.substations (
    substation_id text NOT NULL,
    country_code  text NOT NULL,
    region_code   text NOT NULL,
    name          text NOT NULL,
    operator      text,
    voltage_kv    numeric NOT NULL CHECK (voltage_kv > 0),
    capacity_mva  numeric,
    source_date   date NOT NULL,
    geom          geometry(Point, 25832) NOT NULL,
    qa_run_id     uuid NOT NULL,
    PRIMARY KEY (country_code, substation_id)
);

CREATE TABLE curated.peatland (
    peat_id                 text NOT NULL,
    country_code            text NOT NULL,
    region_code             text NOT NULL,
    peat_class              text NOT NULL,
    peat_depth_cm           numeric,
    soil_organic_carbon_pct numeric,
    source_date             date NOT NULL,
    geom                    geometry(Geometry, 25832) NOT NULL
                            CHECK (ST_IsValid(geom) AND GeometryType(geom) IN ('POLYGON', 'MULTIPOLYGON')),
    qa_run_id               uuid NOT NULL,
    PRIMARY KEY (country_code, peat_id)
);

CREATE TABLE curated.screening (
    site_id               text NOT NULL,
    country_code          text NOT NULL,
    region_code           text NOT NULL,
    parcel_id             text NOT NULL,
    suitability           text NOT NULL,
    eligible_area_m2      numeric NOT NULL CHECK (eligible_area_m2 >= 0),
    eco_point_factor      numeric NOT NULL,
    eco_points_estimate   numeric NOT NULL,
    nearest_substation_id text,
    source_date           date NOT NULL,
    geom                  geometry(Geometry, 25832) NOT NULL
                          CHECK (ST_IsValid(geom) AND GeometryType(geom) IN ('POLYGON', 'MULTIPOLYGON')),
    qa_run_id             uuid NOT NULL,
    PRIMARY KEY (country_code, site_id)
);

CREATE INDEX curated_parcels_geom_idx ON curated.parcels USING gist (geom);
CREATE INDEX curated_substations_geom_idx ON curated.substations USING gist (geom);
CREATE INDEX curated_peatland_geom_idx ON curated.peatland USING gist (geom);
CREATE INDEX curated_screening_geom_idx ON curated.screening USING gist (geom);
