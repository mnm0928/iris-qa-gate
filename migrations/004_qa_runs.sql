CREATE TABLE qa.run (
    run_id              uuid PRIMARY KEY,
    dataset             text NOT NULL,
    profile_name        text NOT NULL,
    profile_sha256      text NOT NULL,
    as_of               date NOT NULL,
    started_at          timestamptz NOT NULL,
    finished_at         timestamptz NOT NULL,
    row_count           integer NOT NULL,
    dataset_fingerprint text NOT NULL,
    decision            text NOT NULL CHECK (decision IN ('PASS', 'WARN', 'BLOCK')),
    promoted            boolean NOT NULL DEFAULT false,
    quarantined_rows    integer NOT NULL DEFAULT 0,
    summary             jsonb NOT NULL
);
CREATE INDEX run_dataset_idx ON qa.run (dataset, started_at DESC);

CREATE TABLE qa.check_result (
    run_id          uuid NOT NULL REFERENCES qa.run (run_id) ON DELETE CASCADE,
    seq             integer NOT NULL,
    check_id        text NOT NULL,
    check_type      text NOT NULL,
    implementation  text NOT NULL CHECK (implementation IN ('sql', 'python')),
    outcome         text NOT NULL CHECK (outcome IN ('PASS', 'WARN', 'BLOCK')),
    violation_count integer NOT NULL,
    message         text NOT NULL,
    evidence        jsonb NOT NULL,
    PRIMARY KEY (run_id, check_id)
);

CREATE TABLE qa.quarantine (
    run_id       uuid NOT NULL REFERENCES qa.run (run_id) ON DELETE CASCADE,
    dataset      text NOT NULL,
    country_code text,
    record_key   text,
    reason       text NOT NULL,
    row_data     jsonb NOT NULL
);
CREATE INDEX quarantine_run_idx ON qa.quarantine (run_id);
