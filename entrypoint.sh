#!/usr/bin/env bash

set -Euo pipefail

export VAULT_S3_TOKEN=$(cat /run/secrets/vault-s3-token)
export OPA_SECRET=$(cat /run/secrets/opa-service-token)

if [[ -f "initial_setup" ]]; then
    if [[ -f "/run/secrets/cert.pem" ]]; then
        CERT=$(head -n 2 /run/secrets/cert.pem | tail -n 1)
        SITE_PKGS=$(python -c 'import site; print(site.getsitepackages()[0])')
        echo $SITE_PKGS
        if grep -q "$CERT" $SITE_PKGS/certifi/cacert.pem
        then
            echo "hi"
            cat /run/secrets/cert.pem >> ${SITE_PKGS}/certifi/cacert.pem
        fi
    fi

    sed -i s@\<CANDIG_OPA_SECRET\>@$OPA_SECRET@ config.ini
    sed -i s@\<OPA_URL\>@$OPA_URL@ config.ini
    sed -i s@\<VAULT_URL\>@$VAULT_URL@ config.ini
    sed -i s@\<CANDIG_AUTHORIZATION\>@$CANDIG_AUTH@ config.ini

    # set up crontab
    sed -i s@\<VAULT_S3_TOKEN\>@$VAULT_S3_TOKEN@ renew_token.sh
    crontab -l > cron_bkp
    echo "0 * * * * bash /app/htsget_server/renew_token.sh" >> cron_bkp
    crontab cron_bkp
    rm cron_bkp
    db=${DB_PATH:-/app/htsget_server/data/files.db}

    # initialize the db if it's not already there:
    sqlite3 -bail /data/files.db "SELECT * from variantfile"
    if [[ $? -eq 1 ]]; then
        echo "initializing database..."
        sqlite3 $db -init /app/htsget_server/data/files.sql "SELECT * from variantfile"
        echo "...done"
    fi

    # if the refseq table isn't filled in the database already, make it:
    numgenes=$(sqlite3 -bail /data/files.db "select * from ncbiRefSeq limit 1;" | wc -l)
    if [[ $numgenes -eq 0 ]]; then
        echo "adding data to ncbiRefSeq..."
        awk '{ print "INSERT OR IGNORE INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, end, gene_name) VALUES (" "\047hg37\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047);"}' data/refseq/ncbiRefSeqSelect.hg37.txt >> genes.sql
        awk '{ print "INSERT OR IGNORE INTO ncbiRefSeq (reference_genome, transcript_name, contig, start, end, gene_name) VALUES (" "\047hg38\047, \047" $1 "\047, \047" $2 "\047, " $3 ", " $4 ", \047" $5 "\047);"}' data/refseq/ncbiRefSeqSelect.hg38.txt >> genes.sql

        cat genes.sql | sqlite3 $db
        rm genes.sql
        echo "...done"
    fi

    rm initial_setup
fi

crond
python3 htsget_server/server.py $@
