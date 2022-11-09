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
    
    sqlite3 ${DB_PATH:-/app/htsget_server/data/files.db} -init /app/htsget_server/data/files.sql "SELECT * from variantfile"
    rm initial_setup
fi

crond
echo '10.182.19.137     ecs.uhn.ca' >> /etc/hosts
python3 htsget_server/server.py $@ 
