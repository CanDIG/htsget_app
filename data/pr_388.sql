-- add the analysis date column if it doesn't already exist
DO
$$
    BEGIN
        ALTER TABLE variantfile ADD COLUMN IF NOT EXISTS analysis_date DATE;
    END;
$$;
