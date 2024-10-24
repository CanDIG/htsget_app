import os
import re
import database
import drs_operations
from candigv2_logging.logging import CanDIGLogger


logger = CanDIGLogger(__file__)


def find_variants_in_region(reference_name=None, start=None, end=None):
    """
    finds variant records in vcf files, returns an array of VcfJson objects
    """

    region = {'referenceName': database.normalize_contig(reference_name)}
    if start is not None:
        region['start'] = int(start) - 1 # search for bases starting at the interbase half-a-base back
    if end is not None:
        region['end'] = int(end)
    raw_result = database.search({
        "region": region
    })
    # raw_result = [{'drs_object_id', 'variantcount', 'reference_genome'}]
    # fetch all relevant results:
    #   group results by variant (chr:start-end)
    #   for boolean/count results, we can just count keys
    #   resultsets require more processing
    variants_by_file = {}
    for result in raw_result:
        variants_by_file[result['drs_object_id']] = parse_vcf_file(result['drs_object_id'], reference_name=region['referenceName'], start=region['start'], end=region['end'])

    # if a file has no variants in it, we don't need to return it:
    final_variants_by_file = {}
    for file in variants_by_file.keys():
        if 'variants' in variants_by_file[file] and len(variants_by_file[file]['variants']) > 0:
            final_variants_by_file[file] = variants_by_file[file]
    return final_variants_by_file


def parse_vcf_file(drs_object_id, reference_name=None, start=None, end=None):
    gen_obj = drs_operations._get_genomic_obj(drs_object_id)
    if "message" in gen_obj:
        raise Exception(f"error parsing vcf file for {drs_object_id}: {gen_obj['message']}")
    if reference_name is not None:
        ref_name = database.get_contig_name_in_variantfile({'refname': reference_name, 'variantfile_id': drs_object_id})
        records = gen_obj['file'].fetch(contig=ref_name, start=start, end=end)
    else:
        records = gen_obj['file'].fetch()
    headers = parse_headers(database.get_headers({'variantfile_id': drs_object_id}))

    variants_by_file = {
        "id": drs_object_id,
        "headers": headers,
        "variants": []
    }
    if 'fileformat' in headers:
        variants_by_file['fileformat'] = headers.pop('fileformat').pop()
    if 'assembly' in headers:
        variants_by_file['assembly'] = headers.pop('assembly').pop()
    if 'INFO' in headers:
        variants_by_file['info'] = headers.pop('INFO')
    if 'FILTER' in headers:
        variants_by_file['filter'] = headers.pop('FILTER')
    if 'FORMAT' in headers:
        variants_by_file['format'] = headers.pop('FORMAT')
    if 'ALT' in headers:
        variants_by_file['alt'] = headers.pop('ALT')
    if 'contig' in headers:
        variants_by_file['contig'] = headers.pop('contig')
    for r in records:
        samples = []
        for s in r.samples:
            if "samples" in gen_obj and s in gen_obj['samples']:
                samples.append(gen_obj['samples'][s])
            else:
                samples.append(s)
        variant_record = parse_variant_record(str(r), samples, variants_by_file['info'])
        variants_by_file['variants'].append(variant_record)
    return variants_by_file


def parse_variant_record(record, samples, info_headers_obj):
    # chr21\t5030551\t.\tA\tC\t.\tPASS\tDP=100;SOMATIC;SS=2;SSC=3;GPV=1;SPV=0.5\tGT:GQ:DP:RD:AD:FREQ:DP4\t0/0:.:55:55:0:0%:25,14,0,0\t0/1:.:90:90:2:2.27%:48,38,1,1\n
    # CHROM POS ID REF ALT QUAL FILTER INFO
    vcf_parse = re.match(r'(.+?)\t(.+?)\t(.+?)\t(.+?)\t(.+?)\t(.+?)\t(.+?)\t(.+?)\t(.+)', record)
    if vcf_parse is not None:
        variant = {
            'chrom': vcf_parse.group(1),
            'pos': vcf_parse.group(2),
            'id': vcf_parse.group(3),
            'ref': vcf_parse.group(4),
            'alt': vcf_parse.group(5).split(','),
            'qual': vcf_parse.group(6),
            'filter': vcf_parse.group(7),
            'info': vcf_parse.group(8),
            'samples': {}
        }
        if vcf_parse.group(9) is not None and vcf_parse.group(9) != "":
            sample_parse = vcf_parse.group(9).split("\t")
            format = sample_parse.pop(0).split(":")
            for s in samples:
                variant['samples'][s] = {}
                sample_parts = sample_parse.pop(0).split(":")
                for f in format:
                    variant['samples'][s][f] = sample_parts.pop(0)
        variant['info'] = process_info_fields(variant['info'], info_headers_obj)
        return variant
    return None


def parse_headers(headers):
    new_obj = {}
    for k in headers:
        meta_parse = re.match(r"##(.+?)=(.+)", k)
        if meta_parse is None:
            continue
        if meta_parse.group(1) not in new_obj:
            new_obj[meta_parse.group(1)] = []
        new_meta = parse_header(meta_parse.group(2))
        new_obj[meta_parse.group(1)].append(new_meta)

    cleaned_obj = {}
    for type in new_obj.keys():
        for entry in new_obj[type]:
            if type not in cleaned_obj:
                cleaned_obj[type] = []
            if entry.pop('structured'):
                new_entry = {}
                for e in entry:
                    new_entry[e.lower()] = entry[e]
                cleaned_obj[type].append(new_entry)
            else:
                cleaned_obj[type].append(entry['value'])
    return cleaned_obj


def parse_header(text):
    new_meta = {}
    metadata_parse = re.match(r"^(<)*(.+?)>*$", text)
    if metadata_parse is not None:
        if metadata_parse.group(1) is not None:
            new_meta['structured'] = True
            fields = metadata_parse.group(2).split(",", 1)
            while len(fields) > 0:
                curr_field = fields.pop(0)
                if "=" in curr_field:
                    [k,v] = curr_field.split("=", 1)
                    if v.startswith('"'):
                        # we're inside a quoted value, so any commas in here are still part of the same value
                        fields.insert(0, v)
                        curr_value = ','.join(fields)
                        curr_value = curr_value[1:] # get rid of opening quote
                        # continue eating through until we get to an unescaped quote
                        new_value = curr_value[0]
                        curr_value = curr_value[1:]
                        while len(curr_value) > 0:
                            if curr_value.startswith('"'):
                                if not new_value.endswith('\\'): # this wasn't an escaped quote
                                    curr_value = curr_value[2:] # 2 because of the next comma
                                    break
                                # it was an escaped quote, so keep going...
                            new_value += curr_value[0]
                            curr_value = curr_value[1:]
                        new_meta[k] = new_value
                        fields = [curr_value]
                        continue
                    else:
                        new_meta[k] = v
                if len(fields) > 0:
                    fields = fields.pop().split(",", 1)
        else:
            new_meta['structured'] = False
            new_meta['value'] = text
    return new_meta


def process_info_fields(text, info_headers_obj):
    info_headers = {}
    for h in info_headers_obj:
        info_headers[h['id']] = h
    # reserved info headers (from VCF spec):
    reserved = [
        ["AA", "1", "String", "Ancestral allele"],
        ["AC", "A", "Integer", "Allele count in genotypes, for each ALT allele, in the same order as listed"],
        ["AD", "R", "Integer", "Total read depth for each allele"],
        ["ADF", "R", "Integer", "Read depth for each allele on the forward strand"],
        ["ADR", "R", "Integer", "Read depth for each allele on the reverse strand"],
        ["AF", "A", "Float", "Allele frequency for each ALT allele in the same order as listed (estimated from primary data, not called genotypes)"],
        ["AN", "1", "Integer", "Total number of alleles in called genotypes"],
        ["BQ", "1", "Float", "RMS base quality"],
        ["CIGAR", "A", "String", "Cigar string describing how to align an alternate allele to the reference allele"],
        ["DB", "0", "Flag", "dbSNP membership"],
        ["DP", "1", "Integer", "Combined depth across samples"],
        ["END", "1", "Integer", "End position on CHROM (used with symbolic alleles; see below)"],
        ["H2", "0", "Flag", "HapMap2 membership"],
        ["H3", "0", "Flag", "HapMap3 membership"],
        ["MQ", "1", "Float", "RMS mapping quality"],
        ["MQ0", "1", "Integer", "Number of MAPQ == 0 reads"],
        ["NS", "1", "Integer", "Number of samples with data"],
        ["SB", "4", "Integer", "Strand bias"],
        ["SOMATIC", "0", "Flag", "Somatic mutation (for cancer genomics)"],
        ["VALIDATED", "0", "Flag", "Validated by follow-up experiment"],
        ["1000G", "0", "Flag", "1000 Genomes membership"]
    ]
    for r in reserved:
        info_headers[r[0]] = {
            "number": r[1],
            "type": r[2],
            "description": r[3]
        }
    info_pieces = text.split(';')
    info_obj = {}
    for info in info_pieces:
        kv = info.split('=', 2)
        if kv[0] in info_headers:
            info_obj[kv[0]] = {
                'type': info_headers[kv[0]]['type'],
                'number': info_headers[kv[0]]['number'],
                'description': info_headers[kv[0]]['description'],
                'value': None
            }
            if len(kv) > 1:
                vals = kv[1].split(',')
                if info_obj[kv[0]]['number'] == '1':
                    info_obj[kv[0]]['value'] = [kv[1]]
                else:
                    info_obj[kv[0]]['value'] = vals

    # find a CSQ header, as a special case:
    csq_header = None
    if 'CSQ' in info_headers:
        csq_header = info_headers['CSQ']['description']
    if 'CSQ' in text and csq_header is not None:
        info_obj['CSQ']['description'] = "Consequence annotations from Ensembl VEP."
        info_obj['CSQ']['value'] = parse_vep_annotation(info_obj['CSQ']['value'], csq_header)
        info_obj['CSQ']['number'] = 'K' # obj keyed by allele

    return info_obj


def parse_vep_annotation(info, csq_header):
    result = {}
    csq_match = re.match(r".+Format: (.+)", csq_header)
    csq_parts = csq_match.group(1).split('|')
    for i in range(len(info)):
        this_info = {}
        info_pieces = info[i].split('|')
        if len(info_pieces) <= len(csq_parts):
            for j in range(len(info_pieces)):
                if info_pieces[j] is not None and info_pieces[j] != '':
                    this_info[csq_parts[j]] = info_pieces[j]
        if this_info['Allele'] not in result:
            result[this_info['Allele']] = []
        result[this_info['Allele']].append(this_info)
    return result


def get_genotype_index(a, b):
    # from VCF spec:
    # genotype ordering: the index of the genotype “a/b”, where a ≤ b, is b(b + 1)/2 + a
    if a > b:
        c = a
        a = b
        b = c
    return ((b * (b + 1)) / 2) + a


def seq_match(a, b):
    return len(set(expand_iupac(a)).intersection(set(expand_iupac(b)))) > 0


def expand_iupac(base_str):
    result = []
    # Find ambiguous nucleotide sequences (https://www.bioinformatics.org/sms/iupac.html) in the given sequence.
    ambig_match = re.match(r"(^.*?)([RYSWKMBDHVN])(.*$)", base_str)
    if ambig_match is None:
        return [base_str]
    # while there is an ambiguity char in group 2, append the expanded seqs to result, then run expand_iupac on each of those results
    # ooh, apparently python 3.10 has match/case:
    match ambig_match.group(2):
        case 'R':
            result.append(f"{ambig_match.group(1)}A{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}G{ambig_match.group(3)}")
        case 'Y':
            result.append(f"{ambig_match.group(1)}C{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}T{ambig_match.group(3)}")
        case 'S':
            result.append(f"{ambig_match.group(1)}G{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}C{ambig_match.group(3)}")
        case 'W':
            result.append(f"{ambig_match.group(1)}A{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}T{ambig_match.group(3)}")
        case 'K':
            result.append(f"{ambig_match.group(1)}G{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}T{ambig_match.group(3)}")
        case 'M':
            result.append(f"{ambig_match.group(1)}A{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}C{ambig_match.group(3)}")
        case 'B':
            result.append(f"{ambig_match.group(1)}A{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}G{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}T{ambig_match.group(3)}")
        case 'D':
            result.append(f"{ambig_match.group(1)}C{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}G{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}T{ambig_match.group(3)}")
        case 'H':
            result.append(f"{ambig_match.group(1)}A{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}C{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}T{ambig_match.group(3)}")
        case 'V':
            result.append(f"{ambig_match.group(1)}A{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}C{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}G{ambig_match.group(3)}")
        case 'N':
            result.append(f"{ambig_match.group(1)}A{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}C{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}G{ambig_match.group(3)}")
            result.append(f"{ambig_match.group(1)}T{ambig_match.group(3)}")
    final = []
    while len(result) > 0:
        final.extend(expand_iupac(result.pop(0)))
    return final


def convert_hgvsid_to_location(hgvsid, reference_genome='hg38'):
    result = {}
    hgvs_parse = re.match(r'(.+):[gc].(\d+)(.+)', hgvsid)
    if hgvs_parse is not None:
        genes = database.search_refseqs(hgvs_parse.group(1), 'transcript_name')
        if genes is None or len(genes) == 0:
            return None
        if len(genes) > 1:
            for gene in genes:
                if gene['reference_genome'] != reference_genome:
                    continue
                result['reference_name'] = database.normalize_contig(gene['contig'])
                result['start'] = int(gene['start']) + int(hgvs_parse.group(2))
                break
        else:
            # this is a chromosome; these belong to only one reference genome
            result['reference_name'] = database.normalize_contig(genes[0]['contig'])
            result['reference_genome'] = genes[0]['reference_genome']
            result['start'] = int(hgvs_parse.group(2))

        # parse allele bit, group(3):
        sub_parse = re.match(r'([A-Z]+)[>=]([A-Z]*)', hgvs_parse.group(3))
        if sub_parse is not None:
            result['ref'] = sub_parse.group(1)
            result['alt'] = sub_parse.group(2)
            result['end'] = result['start'] + len(result['ref'])
            result['type'] = 'SUB'
            return result

        del_parse = re.match(r'_(\d+)del$', hgvs_parse.group(3))
        if del_parse is not None:
            # vcf notates deletions as starting the base before,
            # with the ref as the seq including deleted bases
            # and the alt as the seq without deleted bases
            result['start'] = result['start'] - 1
            result['end'] = int(del_parse.group(1))
            result['ref'] = 'N' * (result['end'] - result['start'])
            result['alt'] = 'N'
            result['type'] = 'DEL'
            return result

        ins_parse = re.match(r'_(\d+)ins([A-Z]+)', hgvs_parse.group(3))
        if ins_parse is not None:
            # vcf notates insertions as starting the base before,
            # with the ref as the leading ref seq base
            # and the alt as the ref base + inserted seq
            result['start'] = result['start'] - 1
            result['ref'] = 'N' + ins_parse.group(2)[0]
            result['alt'] = 'N' + ins_parse.group(2)
            result['end'] = result['start'] + len(result['alt']) + 1
            result['type'] = 'INS'
            return result

        dup_parse = re.match(r'_(\d+)dup', hgvs_parse.group(3))
        if dup_parse is not None:
            result['end'] = (int(dup_parse.group(1)) * 2) - result['start']
            result['type'] = 'DUP'
            return result

        inv_parse = re.match(r'_(\d+)inv', hgvs_parse.group(3))
        if inv_parse is not None:
            result['end'] = int(dup_parse.group(1))
            result['type'] = 'INV'
            return result

        delins_parse = re.match(r'_(\d+)delins([A-Z]+)', hgvs_parse.group(3))
        if delins_parse is not None:
            result['alt'] = delins_parse.group(2)
            result['end'] = int(delins_parse.group(1))
            result['ref'] = 'N' * (result['end'] - result['start'])
            result['type'] = 'DELINS'
            return result

        rep_parse = re.match(r'([A-Z]+)\[(\d+)\]', hgvs_parse.group(3))
        if rep_parse is not None:
            result['ref'] = rep_parse.group(1)
            result['alt'] = rep_parse.group(1) * int(rep_parse.group(2))
            result['end'] = result['start'] + len(rep_parse.group(1))
            result['type'] = 'REP'
            return result
    return None
