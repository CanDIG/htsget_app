-- a drs_object's size can be really big
DO
$$
    BEGIN
        ALTER TABLE cohort ADD COLUMN IF NOT EXISTS statistics jsonb;
    END;
$$;
