#!/usr/bin/env bash

set -Euo pipefail

export VAULT_URL=$VAULT_URL
export AGGREGATE_COUNT_THRESHOLD=$AGGREGATE_COUNT_THRESHOLD

if [[ -f "initial_setup" ]]; then
    sed -i s@\<OPA_URL\>@$OPA_URL@ config.ini
    sed -i s@\<VAULT_URL\>@$VAULT_URL@ config.ini
    sed -i s@\<AGGREGATE_COUNT_THRESHOLD\>@$AGGREGATE_COUNT_THRESHOLD@ config.ini
    sed -i s@\<POSTGRES_USERNAME\>@$POSTGRES_USERNAME@ config.ini

    mkdir -p $INDEXING_PATH
    mkdir -p $SEARCH_PATH/results
    mkdir -p $SEARCH_PATH/to_search
    touch $INDEXING_SWITCH_FILE
    rm initial_setup
fi

bash create_db.sh
python -c "import candigv2_logging.logging
candigv2_logging.logging.initialize()"

# use the following for development
#python3 htsget_server/server.py

bash htsget_server/indexing.sh &
bash htsget_server/search.sh &

# use the following instead for production deployment
cd htsget_server
gunicorn -k uvicorn.workers.UvicornWorker server:app
