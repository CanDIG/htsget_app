import drs_operations
import database
from pysam import VariantFile, AlignmentFile
import argparse
import requests


def index_variants(id_=None, force=False, genome='hg38'):
    varfile = database.get_variantfile(id_)
    if varfile is None:
        varfile = database.create_variantfile({"id": id_, "reference_genome": genome})
    gen_obj = drs_operations._get_genomic_obj(id_)
    if gen_obj is None:
        return {"message": f"No variant with id {id_} exists"}, 404
    if "message" in gen_obj:
        return {"message": gen_obj['message']}, 500
    headers = str(gen_obj['file'].header).split('\n')
    database.add_header_for_variantfile({'texts': headers, 'variantfile_id': id_})
    samples = list(gen_obj['file'].header.samples)
    for sample in samples:
        if database.create_sample({'id': sample, 'variantfile_id': id_}) is None:
            return {"message": f"Could not add sample {sample} to variantfile {id_}"}, 500
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
    for record in gen_obj['file'].fetch():
        normalized_contig_id = contigs[record.contig]
        if normalized_contig_id is not None:
            positions.append(record.pos)
            normalized_contigs.append(normalized_contig_id)
        else:
            app.logger.warning(f"referenceName {record.contig} in {id_} does not correspond to a known chromosome.")
    res = database.create_position({'variantfile_id': id_, 'positions': positions, 'normalized_contigs': normalized_contigs})
    if res is None:
        return {"message": f"Could not add positions {record.contig}:{record.pos} to variantfile {id_}"}, 500
    else:
        database.mark_variantfile_as_indexed(id_)
    return varfile, 200

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="index variant files")

    parser.add_argument("--id", help="drs object id", required=True)
    parser.add_argument("--genome", help="reference genome", default="hg38", required=False)

    args = parser.parse_args()

    print(index_variants(id_=args.id, force=True, genome=args.genome))
