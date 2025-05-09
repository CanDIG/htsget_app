from config import SEARCH_PATH
import os
from watchdog.observers import Observer
import watchdog.events
from candigv2_logging.logging import initialize, CanDIGLogger
import json
from beacon_operations import full_beacon_search
from time import time


logger = CanDIGLogger(__file__)

initialize()


def search_file(file_path):
    json_data = None
    status_code = 500
    results = {}
    results_path = os.path.join(SEARCH_PATH, "results", os.path.basename(file_path))
    try:
        with open(file_path) as f:
            json_data = json.load(f)
        if json_data is not None:
            logger.info(f"Searching {file_path}")
            results["result"] = full_beacon_search(json_data)
            results["complete"] = True
        os.remove(file_path)
    except Exception as e:
        message = f"Couldn't load data from {file_path}: {type(e)} {str(e)}"
        logger.error(message)
        results["error"] = message
        status_code = 500
    with open(results_path, "w") as f:
        json.dump(results, f)

    # clean up old search results
    results_path = os.path.join(SEARCH_PATH, "results")
    for filename in os.listdir(results_path):
        file_path = os.path.join(results_path, filename)
        filestamp = os.stat(file_path).st_mtime
        seven_days_ago = time() - 7 * 86400
        if filestamp < seven_days_ago:
            os.remove(file_path)
    return results, status_code


class SearchHandler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        search_file(event.src_path)


if __name__ == "__main__":
    ## look for any backlog IDs, search those, then listen for new IDs to search.
    search_path = os.path.join(SEARCH_PATH, "to_search")
    logger.info(f"searching started on {search_path}")
    to_search = os.listdir(search_path)
    logger.info(f"Finishing backlog: searching {to_search}")
    while len(to_search) > 0:
        try:
            file_path = f"{search_path}/{to_search.pop()}"
            search_file(file_path)
        except Exception as e:
            logger.warning(str(e))
        to_search = os.listdir(search_path)

    # now that the backlog is complete, listen for new files created:
    logger.info(f"listening for new files at {search_path}")
    event_handler = SearchHandler()
    observer = Observer()
    observer.schedule(event_handler, search_path, recursive=False)
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
