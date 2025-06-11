-- add the metadata column if it doesn't already exist
DO
$$
    BEGIN
        ALTER TABLE drs_object ADD COLUMN IF NOT EXISTS meta_data jsonb;
    END;
$$;
