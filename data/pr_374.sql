DO
$$
    BEGIN
        -- remove the old primary key on the serial id and make a composite pkey on
        -- contig_id + pos_bucket_id
        ALTER TABLE pos_bucket_variantfile_association DROP CONSTRAINT pos_bucket_variantfile_association_pos_bucket_id_fkey;
        ALTER TABLE pos_bucket DROP CONSTRAINT pos_bucket_pkey;
        ALTER TABLE pos_bucket ADD CONSTRAINT pos_bucket_unique UNIQUE (id);
        ALTER TABLE pos_bucket ALTER COLUMN id SET NOT NULL;
        ALTER TABLE pos_bucket ADD CONSTRAINT pos_bucket_pkey PRIMARY KEY (contig_id, pos_bucket_id);
        ALTER TABLE pos_bucket_variantfile_association ADD CONSTRAINT pos_bucket_variantfile_association_pos_bucket_id_fkey FOREIGN KEY (pos_bucket_id) REFERENCES pos_bucket (id);
    END;
$$;
