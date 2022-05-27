#!/usr/bin/env bash

set -Euo pipefail

export VAULT_S3_TOKEN=$(cat /run/secrets/vault-s3-token)

if [[ -f "initial_setup" ]]; then
    if [[ -f "/run/secrets/cert.pem" ]]; then
        cat /run/secrets/cert.pem >> /usr/local/lib/python3.7/site-packages/certifi/cacert.pem
    fi
    
    ACCESS=$(cat /run/secrets/access)
    sed -i s@\<MINIO_ACCESS_KEY\>@$ACCESS@ config.ini
    
    SECRET=$(cat /run/secrets/secret)
    sed -i s@\<MINIO_SECRET_KEY\>@$SECRET@ config.ini
    
    # set up crontab
    sed -i s@\<VAULT_S3_TOKEN\>@$VAULT_S3_TOKEN@ renew_token.sh
    crontab -l > cron_bkp
    echo "0 */3 * * * bash /app/htsget_server/renew_token.sh" >> cron_bkp
    crontab cron_bkp
    rm cron_bkp
    
    rm initial_setup
fi

python3 htsget_server/server.py $@