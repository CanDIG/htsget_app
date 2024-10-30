until python htsget_server/indexing.py; do
    if [[ $? != 10 ]]; then
        echo "Indexing crashed with exit code $?.  Respawning..." >&2
    fi
    sleep 10
done