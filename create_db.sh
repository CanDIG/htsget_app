#!/usr/bin/env bash

set -Euo pipefail

# db=${DB_PATH:-data/files.db}
db=${DB_PATH:-"metadata-db"}

# PGPASSWORD is used by psql to avoid the password prompt
export PGPASSWORD=${PGPASSWORD:-`cat $POSTGRES_PASSWORD_FILE`}
export PGUSER=$POSTGRES_USERNAME

until pg_isready -h "$db" -p 5432 -U $PGUSER; do
  echo "Waiting for the database at $db to be ready..."
  sleep 1
done

echo "database is at $db"
pwd

# initialize the db if it's not already there:
psql --quiet -h "$db" -U $PGUSER -d genomic -c "SELECT * from ncbirefseq limit 1"
if [[ $? -ne 0 ]]; then
    echo "initializing database..."
    createdb -h "$db" -U $PGUSER genomic
    psql --quiet -h "$db" -U $PGUSER -a -d genomic -f data/files.sql >>setup_out.txt
    echo "...done"
fi

# if the refseq table isn't filled in the database already, make it:
numgenes=$(psql --quiet -h "$db" -U $PGUSER -d genomic -c "select * from ncbirefseq where gene_name != '' limit 1;" | wc -l)
if [[ $numgenes -lt 5 ]]; then
    echo "adding data to ncbirefseq..."
    awk '{ print "INSERT INTO ncbirefseq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES (" "\047hg37\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047) ON CONFLICT DO NOTHING;"}' data/refseq/ncbiRefSeqSelect.hg37.txt >> genes.sql
    awk '{ print "INSERT INTO ncbirefseq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES (" "\047hg38\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047) ON CONFLICT DO NOTHING;"}' data/refseq/ncbiRefSeqSelect.hg38.txt >> genes.sql

    psql --quiet -h "$db" -U $PGUSER -d genomic -a -f genes.sql >>setup_out.txt
    # rm genes.sql
    echo "...done"
fi

# run any migrations:
echo "running migrations..."
psql --quiet -h "$db" -U $PGUSER -d genomic -a -f data/pr_288.sql >>setup_out.txt
echo "...done"
