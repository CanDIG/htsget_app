import drs_operations
import database
from pysam import VariantFile, AlignmentFile
import argparse
import requests
import datetime


def index_variants(id_=None, genome='hg38'):
    varfile = database.get_variantfile(id_)
    if varfile is None:
        varfile = database.create_variantfile({"id": id_, "reference_genome": genome})
    print(f"{datetime.datetime.today()} starting indexing")
    gen_obj = drs_operations._get_genomic_obj(id_)
    if gen_obj is None:
        return {"message": f"No variant with id {id_} exists"}, 404
    if "message" in gen_obj:
        return {"message": gen_obj['message']}, 500

    headers = str(gen_obj['file'].header).split('\n')

    database.add_header_for_variantfile({'texts': headers, 'variantfile_id': id_})
    print(f"{datetime.datetime.today()} indexed {len(headers)} headers")

    samples = list(gen_obj['file'].header.samples)
    for sample in samples:
        if database.create_sample({'id': sample, 'variantfile_id': id_}) is None:
            app.logger.warning(f"Could not add sample {sample} to variantfile {id_}")

    print(f"{datetime.datetime.today()} indexed varfile {len(samples)} samples")

    print(f"{datetime.datetime.today()} normalizing contigs")
    contigs = {}
    for contig in list(gen_obj['file'].header.contigs):
        contigs[contig] = database.normalize_contig(contig)

    # find first normalized contig and set the chr_prefix:
    for raw_contig in contigs.keys():
        if contigs[raw_contig] is not None:
            prefix = database.get_contig_prefix(raw_contig)
            varfile = database.set_variantfile_prefix({"variantfile_id": id_, "chr_prefix": prefix})
            break

    print(f"{datetime.datetime.today()} collecting positions")
    positions = []
    normalized_contigs = []
    to_create = {'variantfile_id': id_, 'positions': positions, 'normalized_contigs': normalized_contigs}
    for record in gen_obj['file'].fetch():
        normalized_contig_id = contigs[record.contig]
        if normalized_contig_id is not None:
            positions.append(record.pos)
            normalized_contigs.append(normalized_contig_id)
        else:
            app.logger.warning(f"referenceName {record.contig} in {id_} does not correspond to a known chromosome.")
    res = create_position(to_create)

    print(f"{datetime.datetime.today()} writing {len(res['bucket_counts'])} entries to db")
    database.create_pos_bucket(res)

    database.mark_variantfile_as_indexed(id_)
    print(f"{datetime.datetime.today()} done")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="index variant files")

    parser.add_argument("--id", help="drs object id", required=True)
    parser.add_argument("--genome", help="reference genome", default="hg38", required=False)

    args = parser.parse_args()
    index_variants(id_=args.id, genome=args.genome)
