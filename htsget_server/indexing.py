import drs_operations
import database
from config import INDEXING_PATH
from pysam import VariantFile, AlignmentFile
import argparse
import os
import sys
from watchdog.observers import Observer
import watchdog.events
import hashlib
import re
import datetime
from candigv2_logging.logging import initialize, CanDIGLogger


logger = CanDIGLogger(__file__)

initialize()


def index_variants(file_name=None):
    # split file name into cohort and drs_obj_id
    file_parse = re.match(r"(.*?)_(.+)", file_name)
    if file_parse is not None:
        cohort = file_parse.group(1)
        drs_obj_id = file_parse.group(2)
    else:
        return {"message": f"Format of file name is wrong: {file_name}"}, 500

    logger.log_message("INFO",f"adding stats to {drs_obj_id}")
    calculate_stats(drs_obj_id)
    logger.log_message("INFO",f"{drs_obj_id} stats done")

    gen_obj = drs_operations._get_genomic_obj(drs_obj_id)
    if gen_obj is None:
        return {"message": f"No variant with id {drs_obj_id} exists"}, 404
    if "message" in gen_obj:
        return {"message": gen_obj['message']}, 500

    if gen_obj['type'] == 'read':
        return {"message": f"Read object {drs_obj_id} stats calculated"}, 200

    logger.log_message("INFO",f"{drs_obj_id} starting indexing")

    headers = str(gen_obj['file'].header).split('\n')

    database.add_header_for_variantfile({'texts': headers, 'variantfile_id': drs_obj_id})
    logger.log_message("INFO",f"{drs_obj_id} indexed {len(headers)} headers")

    samples = list(gen_obj['file'].header.samples)
    for sample in samples:
        if database.create_sample({'id': sample, 'variantfile_id': drs_obj_id}) is None:
            logger.log_message("WARNING",f"Could not add sample {sample} to variantfile {drs_obj_id}")

    logger.log_message("INFO",f"{drs_obj_id} indexed {len(samples)} samples in file")

    contigs = {}
    for contig in list(gen_obj['file'].header.contigs):
        contigs[contig] = database.normalize_contig(contig)

    # find first normalized contig and set the chr_prefix:
    for raw_contig in contigs.keys():
        if contigs[raw_contig] is not None:
            prefix = database.get_contig_prefix(raw_contig)
            varfile = database.set_variantfile_prefix({"variantfile_id": drs_obj_id, "chr_prefix": prefix})
            break

    positions = []
    normalized_contigs = []
    to_create = {'variantfile_id': drs_obj_id, 'positions': positions, 'normalized_contigs': normalized_contigs}
    for record in gen_obj['file'].fetch():
        normalized_contig_id = contigs[record.contig]
        if normalized_contig_id is not None:
            positions.append(record.pos)
            normalized_contigs.append(normalized_contig_id)
        else:
            logger.log_message("WARNING",f"referenceName {record.contig} in {drs_obj_id} does not correspond to a known chromosome.")
    res = create_position(to_create)

    logger.log_message("INFO",f"{drs_obj_id} writing {len(res['bucket_counts'])} entries to db")
    database.create_pos_bucket(res)

    database.mark_variantfile_as_indexed(drs_obj_id)
    logger.log_message("INFO",f"{drs_obj_id} done")

    return {"message": f"Indexing complete for variantfile {drs_obj_id}"}, 200


def create_position(obj):
    # obj = { 'variantfile_id',
    #         'position_id' or 'positions',
    #         'normalized_contig_id' or 'normalized_contigs'
    #         }
    if 'position_id' in obj and 'normalized_contig_id' in obj:
        obj['pos_bucket_ids'] = [database.get_bucket_for_position(obj['position_id'])]
        obj.pop('position_id')
        obj['normalized_contigs'] = [obj['normalized_contig_id']]
        obj.pop('normalized_contig_id')
    if len(obj['positions']) != len(obj['normalized_contigs']):
        return None
    old_normalized_contigs = obj.pop('normalized_contigs')
    pos_bucket_ids = [database.get_bucket_for_position(obj['positions'].pop(0))]
    normalized_contigs = [old_normalized_contigs.pop(0)]
    bucket_counts = [0]
    curr_bucket = None
    curr_contig = None
    for i in range(len(obj['positions'])):
        curr_bucket = database.get_bucket_for_position(obj['positions'][i])
        curr_contig = old_normalized_contigs[i]
        bucket_counts[-1] += 1
        if curr_contig != normalized_contigs[-1] or curr_bucket != pos_bucket_ids[-1]:
            pos_bucket_ids.append(curr_bucket)
            bucket_counts.append(0)
            normalized_contigs.append(curr_contig)
    # last position needs to be counted as well
    bucket_counts[-1] += 1
    obj['pos_bucket_ids'] = pos_bucket_ids
    obj['bucket_counts'] = bucket_counts
    obj['normalized_contigs'] = normalized_contigs
    obj.pop('positions')
    return obj


## Given a DrsObject in json, compute its size and checksums
def calculate_stats(obj_id):
    drs_json = database.get_drs_object(obj_id)
    # a DrsObject either has access methods or contents
    if "access_methods" in drs_json:
        # if there are access methods, it's a file object
        file_obj = drs_operations._get_file_path(drs_json["id"])
        if file_obj["checksum"] is None:
            logger.log_message("DEBUG",f"calculating checksum for {drs_json['id']}")
            checksum = []
            with open(file_obj["path"], "rb") as f:
                bytes = f.read()  # read file as bytes
                checksum = [{
                    "type": "sha-256",
                    "checksum": hashlib.sha256(bytes).hexdigest()
                }]
            logger.log_message("DEBUG",f"done calculating checksum for {drs_json['id']}")
            drs_json["checksums"] = checksum
        else:
            drs_json["checksums"] = [file_obj["checksum"]]
        drs_json["size"] = file_obj["size"]
    elif "contents" in drs_json:
        drs_json["size"] = 0
        checksum = {
            "type": "sha-256",
            "checksum": ""
        }
        # if it's a sample drs object, its checksum will be ""
        if drs_json["description"] != "sample":
            # for each contents, find drs_obj for its drs_uri
            raw_checksums = []
            for c in drs_json["contents"]:
                c_obj = calculate_stats(c["name"])
                if len(c_obj["checksums"]) > 0:
                    raw_checksums.append(c_obj["checksums"][0]["checksum"])
                drs_json["size"] += c_obj["size"]
            # sort raw checksums, concat, then take sha256:
            raw_checksums.sort()
            checksum["checksum"] = hashlib.sha256("".join(raw_checksums).encode()).hexdigest()
        drs_json["checksums"] = [checksum]
    return database.create_drs_object(drs_json)


## When a file is created, index the variant with the ID of that filename.
## These are created at htsget_operations.index_variants.
def index_touch_file(file_path):
    try:
        name = file_path.replace(INDEXING_PATH, "").replace("/", "")
        response, status_code = index_variants(file_name=name)
        if status_code != 200:
            with open(file_path, "a") as f:
                f.write(f"{datetime.datetime.today()} {response['message']}")
        logger.log_message("INFO",response)
        os.remove(file_path)
    except Exception as e:
        with open(file_path, "a") as f:
            f.write(f"{datetime.datetime.today()} {str(e)}")
        logger.log_message("WARNING",str(e))


class IndexingHandler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        index_touch_file(event.src_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="index variant files")

    parser.add_argument("--id", help="drs object id", required=False)
    parser.add_argument("--genome", help="reference genome", default="hg38", required=False)

    args = parser.parse_args()

    ## If this has been called on a single ID, index it and exit.
    if args.id is not None:
        drs_obj = database.get_drs_object(args.id)
        if drs_obj is None:
            print(f"No DRS object with id {args.id}")
            sys.exit()
        cohort = ""
        if "cohort" in drs_obj:
            cohort = drs_obj["cohort"]
        varfile = database.create_variantfile({"id": args.id, "reference_genome": args.genome})
        index_variants(drs_obj_id=f"{cohort}_{args.id}")
        sys.exit()

    ## Otherwise, look for any backlog IDs, index those, then listen for new IDs to index.
    logger.log_message("INFO",f"indexing started on {INDEXING_PATH}")
    to_index = os.listdir(INDEXING_PATH)
    logger.log_message("INFO",f"Finishing backlog: indexing {to_index}")
    while len(to_index) > 0:
        try:
            file_path = f"{INDEXING_PATH}/{to_index.pop()}"
            index_touch_file(file_path)
        except Exception as e:
            logger.log_message("WARNING",str(e))
        to_index = os.listdir(INDEXING_PATH)

    # now that the backlog is complete, listen for new files created:
    logger.log_message("INFO",f"listening for new files at {INDEXING_PATH}")
    event_handler = IndexingHandler()
    observer = Observer()
    observer.schedule(event_handler, INDEXING_PATH, recursive=False)
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
