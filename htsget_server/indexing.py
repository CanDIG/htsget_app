import drs_operations
import htsget_operations
import database
from config import INDEXING_PATH, INDEXING_SWITCH_FILE
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
from time import sleep
from random import randint


logger = CanDIGLogger(__file__)

initialize()


def index_variants(file_name=None):
    # split file name into program and drs_obj_id
    file_parse = re.match(r"(.*?)~(.+)", file_name)
    if file_parse is not None:
        program = file_parse.group(1)
        drs_obj_id = file_parse.group(2)
    else:
        return {"message": f"Format of file name is wrong: {file_name}"}, 500

    gen_obj = htsget_operations.get_pysam_obj(drs_obj_id)
    if gen_obj is None:
        return {"message": f"No id {drs_obj_id} exists"}, 404
    if "message" in gen_obj:
        return {"message": gen_obj['message']}, 500

    if gen_obj['type'] == 'read':
        return {"message": f"Read object {drs_obj_id} stats calculated"}, 200

    logger.info(f"{drs_obj_id} starting indexing")

    headers = str(gen_obj['file'].header).split('\n')

    database.add_header_for_variantfile({'texts': headers, 'variantfile_id': drs_obj_id})
    logger.info(f"{drs_obj_id} indexed {len(headers)} headers")

    samples = list(gen_obj['file'].header.samples)
    for sample in samples:
        if database.create_sample({'id': sample, 'variantfile_id': drs_obj_id}) is None:
            logger.warning(f"Could not add sample {sample} to variantfile {drs_obj_id}")

    logger.info(f"{drs_obj_id} indexed {len(samples)} samples in file")

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
            logger.warning(f"referenceName {record.contig} in {drs_obj_id} does not correspond to a known chromosome.")
    res = create_position(to_create)

    logger.info(f"{drs_obj_id} writing {len(res['bucket_counts'])} entries to db")
    write_pos_bucket(res, drs_obj_id)
    mark_as_indexed(drs_obj_id)
    logger.info(f"{drs_obj_id} indexing done")

    return {"message": f"Indexing complete for variantfile {drs_obj_id}"}, 200


def mark_as_indexed(drs_obj_id):
    response, status_code = drs_operations.get_object(drs_obj_id)
    if status_code == 200:
        obj = response.json()
        obj["metadata"]["indexed"] = 1
        drs_operations.post_object(obj)


def write_pos_bucket(obj, object_id, tries=1):
    if tries > 3:
        raise Exception(f"Exception in write_pos_bucket {object_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        database.create_pos_buckets_for_variantfile(obj)
    except Exception as e:
        logger.debug(f"Exception in write_pos_bucket {object_id}: {str(e)}, trying again")
        return write_pos_bucket(obj, object_id, tries=tries+1)


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


## When a file is created, index the variant with the ID of that filename.
## These are created at htsget_operations.index_variants.
def index_touch_file(file_path):
    try:
        name = file_path.replace(INDEXING_PATH, "").replace("/", "")
        logger.info(f"indexing {name}, {str(len(os.listdir(INDEXING_PATH)))} files left in indexing queue. For full list of files to index, run: `docker exec candigv2_htsget_1 ls {INDEXING_PATH}`")
        response, status_code = index_variants(file_name=name)
        if status_code != 200:
            with open(file_path, "a") as f:
                f.write(f"{datetime.datetime.today()} {response['message']}")
        logger.info(response)
        os.remove(file_path)
    except Exception as e:
        with open(file_path, "a") as f:
            f.write(f"{datetime.datetime.today()} {str(e)}")
        logger.warning(f"indexing error! {type(e)} {str(e)}")


class IndexingHandler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        index_touch_file(event.src_path)


if __name__ == "__main__":
    ## if the indexing_on file is not present, exit
    if not os.path.isfile(INDEXING_SWITCH_FILE):
        logger.debug(f"{INDEXING_SWITCH_FILE} is not present; exiting")
        sys.exit(10)

    ## Otherwise, look for any backlog IDs, index those, then listen for new IDs to index.
    logger.info(f"indexing started on {INDEXING_PATH}")
    to_index = os.listdir(INDEXING_PATH)
    logger.info(f"Finishing backlog: indexing {to_index}")
    while len(to_index) > 0:
        try:
            file_path = f"{INDEXING_PATH}/{to_index.pop()}"
            index_touch_file(file_path)
        except Exception as e:
            logger.warning(str(e))
        to_index = os.listdir(INDEXING_PATH)

    # now that the backlog is complete, listen for new files created:
    logger.info(f"listening for new files at {INDEXING_PATH}")
    event_handler = IndexingHandler()
    observer = Observer()
    observer.schedule(event_handler, INDEXING_PATH, recursive=False)
    observer.start()
    try:
        while observer.is_alive():
            ## if the indexing_on file is not present, exit
            if not os.path.isfile(INDEXING_SWITCH_FILE):
                logger.debug(f"{INDEXING_SWITCH_FILE} is not present; exiting")
                sys.exit(10)
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
