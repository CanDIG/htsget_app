-- reverting https://github.com/CanDIG/htsget_app/pull/239
DO
$$
    BEGIN
        ALTER TABLE variantfile DROP COLUMN genomic_id;
    EXCEPTION
        WHEN undefined_column THEN
     END;
$$;
