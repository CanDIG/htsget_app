#!/usr/bin/env bash

set -Euo pipefail

db=${DB_PATH:-data/files.db}

echo "database is at $db"
pwd

# initialize the db if it's not already there:
sqlite3 -bail $db "SELECT * from ncbiRefSeq limit 1"
if [[ $? -eq 1 ]]; then
    echo "initializing database..."
    sqlite3 $db -init data/files.sql "SELECT * from variantfile"
    chown -R candig:candig $(dirname $db)
    echo "...done"
fi

# if the refseq table isn't filled in the database already, make it:
numgenes=$(sqlite3 -bail $db 'select * from ncbiRefSeq where gene_name != "" limit 1;' | wc -l)
if [[ $numgenes -eq 0 ]]; then
    echo "adding data to ncbiRefSeq..."
    awk '{ print "INSERT OR IGNORE INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, end, gene_name) VALUES (" "\047hg37\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047);"}' data/refseq/ncbiRefSeqSelect.hg37.txt >> genes.sql
    awk '{ print "INSERT OR IGNORE INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, end, gene_name) VALUES (" "\047hg38\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047);"}' data/refseq/ncbiRefSeqSelect.hg38.txt >> genes.sql

    sqlite3 $db < genes.sql
    rm genes.sql
    echo "...done"
fi