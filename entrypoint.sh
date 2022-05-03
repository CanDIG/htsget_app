#!/usr/bin/env bash

set -Euo pipefail

if [[ -f "initial_setup" ]]; then
	if [[ -f "/run/secrets/cert.pem" ]]; then
		cat /run/secrets/cert.pem >> /usr/local/lib/python3.7/site-packages/certifi/cacert.pem
	fi
	
	ACCESS=$(cat /run/secrets/access)
	sed -i s@\<MINIO_ACCESS_KEY\>@$ACCESS@ config.ini
	
	SECRET=$(cat /run/secrets/secret)
	sed -i s@\<MINIO_SECRET_KEY\>@$SECRET@ config.ini
	rm initial_setup
fi

python3 htsget_server/server.py $@