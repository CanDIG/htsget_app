BEGIN TRANSACTION;
CREATE TABLE program (
    id VARCHAR NOT NULL,
    statistics JSONB,
    PRIMARY KEY (id)
);
CREATE TABLE drs_object (
        id VARCHAR NOT NULL,
        name VARCHAR,
        self_uri VARCHAR,
        size BIGINT,
        created_time VARCHAR,
        updated_time VARCHAR,
        version VARCHAR,
        mime_type VARCHAR,
        checksums VARCHAR,
        description VARCHAR,
        aliases VARCHAR,
        program_id VARCHAR,
        meta_data JSONB,
        PRIMARY KEY (id),
        FOREIGN KEY(program_id) REFERENCES program (id)
);
CREATE TABLE access_method (
        id SERIAL PRIMARY KEY,
        drs_object_id VARCHAR,
        type VARCHAR,
        access_id VARCHAR,
        region VARCHAR,
        url VARCHAR,
        headers VARCHAR,
        FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);
CREATE TABLE content_object (
        id SERIAL PRIMARY KEY,
        drs_object_id VARCHAR,
        name VARCHAR,
        contents_id VARCHAR,
        drs_uri VARCHAR,
        contents VARCHAR,
        FOREIGN KEY(drs_object_id) REFERENCES drs_object (id)
);

COMMIT;
