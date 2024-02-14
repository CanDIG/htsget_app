import drs_operations
import database
from config import INDEXING_PATH
from pysam import VariantFile, AlignmentFile
import argparse
import logging
import os
import sys
from watchdog.observers import Observer
import watchdog.events


def index_variants(id_=None):
    logging.info(f"{id_} starting indexing")
    gen_obj = drs_operations._get_genomic_obj(id_)
    if gen_obj is None:
        return {"message": f"No variant with id {id_} exists"}, 404
    if "message" in gen_obj:
        return {"message": gen_obj['message']}, 500

    headers = str(gen_obj['file'].header).split('\n')

    database.add_header_for_variantfile({'texts': headers, 'variantfile_id': id_})
    logging.info(f"{id_} indexed {len(headers)} headers")

    samples = list(gen_obj['file'].header.samples)
    for sample in samples:
        if database.create_sample({'id': sample, 'variantfile_id': id_}) is None:
            logging.warning(f"Could not add sample {sample} to variantfile {id_}")

    logging.info(f"{id_} indexed {len(samples)} samples in file")

    contigs = {}
    for contig in list(gen_obj['file'].header.contigs):
        contigs[contig] = database.normalize_contig(contig)

    # find first normalized contig and set the chr_prefix:
    for raw_contig in contigs.keys():
        if contigs[raw_contig] is not None:
            prefix = database.get_contig_prefix(raw_contig)
            varfile = database.set_variantfile_prefix({"variantfile_id": id_, "chr_prefix": prefix})
            break

    positions = []
    normalized_contigs = []
    to_create = {'variantfile_id': id_, 'positions': positions, 'normalized_contigs': normalized_contigs}
    for record in gen_obj['file'].fetch():
        normalized_contig_id = contigs[record.contig]
        if normalized_contig_id is not None:
            positions.append(record.pos)
            normalized_contigs.append(normalized_contig_id)
        else:
            logging.warning(f"referenceName {record.contig} in {id_} does not correspond to a known chromosome.")
    res = create_position(to_create)

    logging.info(f"{id_} writing {len(res['bucket_counts'])} entries to db")
    database.create_pos_bucket(res)

    database.mark_variantfile_as_indexed(id_)
    logging.info(f"{id_} done")
    return {"message": f"Indexing complete for variantfile {id_}"}, 200


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
class IndexingHandler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        name = event.src_path.replace(INDEXING_PATH, "").replace("/", "")
        response, status_code = index_variants(id_=name)
        logging.info(response)
        os.remove(event.src_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=f'%(asctime)s %(levelname)s INDEXING: %(message)s')
    parser = argparse.ArgumentParser(description="index variant files")

    parser.add_argument("--id", help="drs object id", required=False)
    parser.add_argument("--genome", help="reference genome", default="hg38", required=False)

    args = parser.parse_args()

    ## If this has been called on a single ID, index it and exit.
    if args.id is not None:
        varfile = database.create_variantfile({"id": args.id, "reference_genome": args.genome})
        index_variants(id_=args.id)
        sys.exit()

    ## Otherwise, look for any backlog IDs, index those, then listen for new IDs to index.
    logging.info(f"indexing started on {INDEXING_PATH}")
    to_index = os.listdir(INDEXING_PATH)
    logging.info(f"Finishing backlog: indexing {to_index}")
    while len(to_index) > 0:
        index_variants(id_=to_index.pop())
        to_index = os.listdir(INDEXING_PATH)

    # now that the backlog is complete, listen for new files created:
    logging.info(f"listening for new files at {INDEXING_PATH}")
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
