#!/usr/bin/env bash

set -Euo pipefail

# db=${DB_PATH:-data/files.db}
db="metadata-db"

# PGPASSWORD is used by psql to avoid the password prompt
export PGPASSWORD=`cat /run/secrets/metadata-db-secret`
export PGUSER=`cat /run/secrets/metadata-db-user`

until pg_isready -h metadata-db -p 5432 -U $PGUSER; do
  echo "Waiting for the database to be ready..."
  sleep 1
done

echo "database is at $db"
pwd

# initialize the db if it's not already there:
psql -h $db -U $PGUSER -d genomic -c "SELECT * from ncbiRefSeq limit 1"
if [[ $? -ne 0 ]]; then
    echo "initializing database..."
    createdb -h $db -U $PGUSER genomic
    psql -h $db -U $PGUSER -a -d genomic -f data/files.sql
    echo "...done"
fi

# if the refseq table isn't filled in the database already, make it:
numgenes=$(psql -h $db -U $PGUSER -d genomic -c 'select * from ncbiRefSeq where gene_name != "" limit 1;' | wc -l)
if [[ $numgenes -eq 0 ]]; then
    echo "adding data to ncbiRefSeq..."
    awk '{ print "INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES (" "\047hg37\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047) ON CONFLICT DO NOTHING;"}' data/refseq/ncbiRefSeqSelect.hg37.txt >> genes.sql
    awk '{ print "INSERT INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, endpos, gene_name) VALUES (" "\047hg38\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047) ON CONFLICT DO NOTHING;"}' data/refseq/ncbiRefSeqSelect.hg38.txt >> genes.sql

    psql -h $db -U $PGUSER -d genomic -a -f genes.sql
    rm genes.sql
    echo "...done"
fi