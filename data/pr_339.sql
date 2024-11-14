-- add the statistics column if it doesn't already exist
DO
$$
    BEGIN
        ALTER TABLE cohort ADD COLUMN IF NOT EXISTS statistics jsonb;
    END;
$$;
