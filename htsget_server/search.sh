until python htsget_server/search.py; do
    status=$?
    if [[ $status != 10 ]]; then
        echo "Search crashed with exit code $status.  Respawning..." >&2
    else
        echo "search OFF"
    fi
    sleep 10
done