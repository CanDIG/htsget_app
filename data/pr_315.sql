-- a drs_object's size can be really big
DO
$$
    BEGIN
        ALTER TABLE drs_object ALTER size TYPE bigint;
    END;
$$;
