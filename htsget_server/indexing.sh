until python htsget_server/indexing.py; do
    echo "Indexing crashed with exit code $?.  Respawning.." >&2
    sleep 1
done