until python htsget_server/indexing.py; do
    status=$?
    if [[ $status != 10 ]]; then
        echo "Indexing crashed with exit code $status.  Respawning..." >&2
    else
        echo "indexer OFF"
    fi
    sleep 10
done