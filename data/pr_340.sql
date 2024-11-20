-- the table formerly named cohort should be named program
DO
$$
    BEGIN
        ALTER TABLE IF EXISTS cohort RENAME TO program;
        ALTER TABLE drs_object RENAME COLUMN cohort_id to program_id;
    END;
$$;
