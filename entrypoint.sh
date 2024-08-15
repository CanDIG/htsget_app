#!/usr/bin/env bash

set -Euo pipefail

export VAULT_URL=$VAULT_URL
export AGGREGATE_COUNT_THRESHOLD=$AGGREGATE_COUNT_THRESHOLD

if [[ -f "initial_setup" ]]; then
    sed -i s@\<OPA_URL\>@$OPA_URL@ config.ini
    sed -i s@\<VAULT_URL\>@$VAULT_URL@ config.ini
    sed -i s@\<AGGREGATE_COUNT_THRESHOLD\>@$AGGREGATE_COUNT_THRESHOLD@ config.ini
    sed -i s@\<POSTGRES_USERNAME\>@$POSTGRES_USERNAME@ config.ini

    bash create_db.sh
    mkdir $INDEXING_PATH
    rm initial_setup
fi

python -c "import candigv2_logging.logging
candigv2_logging.logging.initialize()"

# use the following for development
#python3 htsget_server/server.py

python htsget_server/indexing.py &

# use the following instead for production deployment
uwsgi uwsgi.ini