CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS qa;

CREATE TABLE ref.region (
    country_code text NOT NULL,
    region_code  text NOT NULL,
    name         text NOT NULL,
    geom         geometry(MultiPolygon, 25832) NOT NULL,
    PRIMARY KEY (country_code, region_code)
);
CREATE INDEX region_geom_idx ON ref.region USING gist (geom);

INSERT INTO ref.region (country_code, region_code, name, geom) VALUES (
    'DE', 'DE-NI', 'Niedersachsen pilot extent',
    ST_Multi(ST_MakeEnvelope(400000, 5750000, 600000, 5900000, 25832))
);
