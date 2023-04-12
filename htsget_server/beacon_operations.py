from flask import Flask
import variants
import drs_operations
import htsget_operations
import variants
import database
import json
import re
import connexion


app = Flask(__name__)

API_VERSION = '1.0.0'
BEACON_ID = 'org.candig.htsget.beacon'
SCHEMA = [
    {
        "entityType": "genomicVariant",
        "schema": 'ga4gh-beacon-variant-v2.0.0'
    }
]

# Endpoints
def get_beacon_service_info():
    return {
        "id": BEACON_ID,
        "name": "CanDIG Beacon v2 genomic variants service",
        "type": {
            "group": "org.ga4gh",
            "artifact": "beacon",
            "version": "v2.0.0"
        },
        "description": "A Beacon v2 server for CanDIG genomic data",
        "organization": {
            "name": "CanDIG",
            "url": "https://www.distributedgenomics.ca"
        },
        "version": API_VERSION
    }


# req = {
#     include_result_set_responses: string,
#     pagination: {
#         currentPage: string,
#         limit: int,
#         nextPage: string,
#         previousPage: string,
#         skip: int
#     }
#     requestParameters: {
#       ...
#     }
#     requestedGranularity: string,
#     testMode: boolean
# }


def get_search(
    skip=None,
    limit=None,
    include_result_set_responses=False,
    start=None,
    end=None,
    assembly_id=None,
    reference_name=None,
    reference_bases=None,
    alternate_bases=None,
    variant_min_length=None,
    variant_max_length=None,
    allele=None,
    gene_id=None,
    filters=None
):
    req = {
        "includeResultsetResponses": include_result_set_responses,
        "pagination": {
            "skip": skip,
            "limit": limit
        },
        "query": {
            "requestParameters": {}
        }
    }
    if alternate_bases is not None:
        req['query']['requestParameters']['alternate_bases'] = alternate_bases
    if assembly_id is not None:
        req['query']['requestParameters']['assembly_id'] = assembly_id
    if end is not None:
        req['query']['requestParameters']['end'] = [end]
    if gene_id is not None:
        req['query']['requestParameters']['gene_id'] = gene_id
    if allele is not None:
        req['query']['requestParameters']['genomic_allele_short_form'] = allele
    if reference_bases is not None:
        req['query']['requestParameters']['reference_bases'] = reference_bases
    if reference_name is not None:
        req['query']['requestParameters']['reference_name'] = reference_name
    if start is not None:
        req['query']['requestParameters']['start'] = [start]
    if variant_max_length is not None:
        req['query']['requestParameters']['variant_max_length'] = variant_max_length
    if variant_min_length is not None:
        req['query']['requestParameters']['variant_min_length'] = variant_min_length

    req['requestedGranularity'] = 'record'
    try:
        result = search(req)
        return result, 200
    except Exception as e:
        return {'message': f"{type(e)}: {str(e)}"}, 500


def post_search():
    req = connexion.request.json
    # includeResultsetResponses:
    #   $ref: '#/components/schemas/IncludeResultsetResponses'
    # pagination:
    #   $ref: '#/components/schemas/Pagination'
    # requestParameters:
    #   $ref: '#/components/schemas/RequestParameters'
    # requestedGranularity:
    #   $ref: '#/components/schemas/Granularity'
    # testMode:
    #   $ref: '#/components/schemas/TestMode'
    if 'requestedGranularity' not in req:
        req['requestedGranularity'] = 'record'

    try:
        result = search(req)
        return result, 200
    except Exception as e:
        return {'message': f"{type(e)}: {str(e)}"}, 500


def search(raw_req):
    req = raw_req['query']['requestParameters']
    # pass req in as an htsget search:
    # if we have regions, they would be in reference_name/start/end
    raw_result = None
    meta = {
        'apiVersion': API_VERSION,
        'beaconId': BEACON_ID,
        'receivedRequestSummary': {
            'apiVersion': API_VERSION,
            'requestedSchemas': SCHEMA,
            'requestParameters': json.loads(json.dumps(req))
        },
        'returnedSchemas': SCHEMA
    }
    if 'pagination' in raw_req:
        meta['receivedRequestSummary']['pagination'] = raw_req['pagination']
    if 'requestedGranularity' in raw_req:
        meta['receivedRequestSummary']['requestedGranularity'] = raw_req['requestedGranularity']
        meta['returnedGranularity'] = raw_req['requestedGranularity']
    ## not using includeResultsetResponses for now:
    # if 'includeResultsetResponses' in raw_req:
    #     meta['receivedRequestSummary']['includeResultsetResponses'] = raw_req['includeResultsetResponses']
    response = {
        'meta': meta,
        'responseSummary': {
            'exists': False,
            'numTotalResults': 0
        }
    }

    actual_params = meta['receivedRequestSummary']['requestParameters']
    # some requestParameters are for region search:
    #         assembly_id: string,
    #         end: [integer],
    #         gene_id: string,
    #         genomic_allele_short_form: string,
    #         reference_name: string,
    #         start: [integer],

    actual_params['reference_genome'] = 'hg38'

    if 'assembly_id' in req:
        actual_params['reference_genome'] = req['assembly_id']

    if 'reference_name' in req:
        actual_params['reference_name']=req['reference_name']

    if 'start' in req and len(req['start']) > 0:
        actual_params['start'] = req['start'].pop(0)

    if 'end' in req and len(req['end']) > 0:
        actual_params['end'] = req['end'].pop(0)
    if 'gene_id' in req:
        genes = database.search_refseqs(req['gene_id'].upper(), 'gene_name')
        if len(genes) > 0:
            for gene in genes:
                if gene['reference_genome'] == actual_params['reference_genome']:
                    actual_params['reference_name'] = database.normalize_contig(gene['contig'])
                    actual_params['start'] = gene['start']
                    actual_params['end'] = gene['end']
                    break
        else:
            response = {
                    'error': {
                        'errorMessage': f"no region was found for geneId {req['gene_id']}",
                        'errorCode': 404
                    },
                    'meta': meta
                }
            return response
    if 'genomic_allele_short_form' in req:
        allele_loc = variants.convert_hgvsid_to_location(req['genomic_allele_short_form'], reference_genome=actual_params['reference_genome'])
        if allele_loc is not None:
            actual_params['reference_name'] = allele_loc['reference_name']
            actual_params['start'] = allele_loc['start']
            actual_params['end'] = allele_loc['end']
            # actual_params['type'] = allele_loc['type']
            if 'reference_genome' in allele_loc:
                actual_params['reference_genome'] = allele_loc['reference_genome']
            if 'ref' in allele_loc:
                actual_params['ref'] = allele_loc['ref']
            if 'alt' in allele_loc:
                actual_params['alt'] = allele_loc['alt']

    if 'reference_name' in actual_params and actual_params['reference_name'] is not None:
        # if there is no end specified, assume the end is same as start:
        if 'end' not in actual_params:
            actual_params['end'] = actual_params['start']

        variants_by_file = variants.find_variants_in_region(reference_name=actual_params['reference_name'], start=actual_params['start'], end=actual_params['end'])

        resultset = compile_beacon_resultset(variants_by_file, reference_genome=actual_params['reference_genome'])
        # others are for filtering after:
        #         aminoacidChange: string,
        #         alternate_bases: string,
        #         reference_bases: string,
        #         variant_max_length: integer
        #         variant_min_length: integer
        #         variantType: string

        if actual_params['start'] == actual_params['end']:
            filtered_resultset = []
            for variant in resultset:
                if variant['variation']['location']['interval']['start']['value'] == actual_params['start'] - 1:
                    if variant['variation']['location']['interval']['end']['value'] == actual_params['end']:
                        filtered_resultset.append(variant)
            resultset = filtered_resultset
        if 'alt' in actual_params:
            filtered_resultset = []
            for variant in resultset:
                if variant['variantInternalId'].endswith('='):
                    filtered_resultset.append(variant) # don't filter out ref seqs
                elif variants.seq_match(variant['variation']['state']['sequence'], actual_params['alt']):
                    filtered_resultset.append(variant)
            resultset = filtered_resultset
        if 'ref' in actual_params:
            filtered_resultset = []
            for variant in resultset:
                if variant['variantInternalId'].endswith('='):
                    if variants.seq_match(variant['variation']['state']['sequence'], actual_params['ref']):
                        filtered_resultset.append(variant)
                else:
                    filtered_resultset.append(variant)
            resultset = filtered_resultset


        if len(resultset) > 0:
            response['responseSummary']['numTotalResults'] = len(resultset)
            response['responseSummary']['exists'] = True

        # if the request granularity was "record", check to see that the user is actually authorized to see any datasets:
        response['beaconHandovers'] = []
        for drs_obj in variants_by_file.keys():
            handover, status_code = htsget_operations.get_variants(id_=drs_obj, reference_name=actual_params['reference_name'], start=actual_params['start'], end=actual_params['end'])
            if handover is not None:
                handover['handoverType'] = {'id': 'CUSTOM', 'label': 'HTSGET'}
                response['beaconHandovers'].append(handover)
        if len(response['beaconHandovers']) > 0:
            response['response'] = resultset
        else:
            meta['returnedGranularity'] = 'count'
            response.pop('beaconHandovers')
    else:
        response = {
            'error': {
                'errorMessage': 'no referenceName was provided',
                'errorCode': 404
            },
            'meta': meta
        }
    return response


def compile_beacon_resultset(variants_by_obj, reference_genome="hg38"):
    """
    Each beacon result describes a variation at a specific position:
    resultset = [
        {
          "caseLevelData": [...],
          "identifiers": {
            "genomicHGVSId": "NC_000021.8:g.5031153="
          },
          "variantInternalId": "NC_000021.8:g.5031153=",
          "variation": {
            "location": {
              "interval": {
                "end": {
                  "type": "Number",
                  "value": 5031153
                },
                "start": {
                  "type": "Number",
                  "value": 5031152
                },
                "type": "SequenceInterval"
              },
              "sequence_id": "refseq:NC_000021.8",
              "type": "SequenceLocation"
            },
            "state": {
              "sequence": "G",
              "type": "LiteralSequenceExpression"
            },
            "type": "Allele"
          }
        }
      ]
    """
    resultset = {}
    for drs_obj in variants_by_obj.keys():
        # check to see if this drs_object is authorized:
        x, status_code = drs_operations.get_object(drs_obj)
        is_authed = (status_code == 200)
        if database.get_variantfile(drs_obj)['reference_genome'] != reference_genome:
            continue
        for variant in variants_by_obj[drs_obj]['variants']:
            # parse the variants beacon-style
            variant['variations'] = compile_variations_from_record(ref=variant.pop('ref'), alt=variant.pop('alt'), chrom=variant.pop('chrom'), pos=variant.pop('pos'), reference_genome=reference_genome)
            assign_info_to_variations(variant)

            # the variations in each variant need to be copied out first:
            resultset[drs_obj] = []
            for var in variant['variations']:
                resultset[drs_obj].append(var['hgvsid'])
                if var['hgvsid'] not in resultset:
                    resultset[var['hgvsid']] = {
                        'variation': {
                            "location": var.pop('location'),
                            "state": var.pop('state'),
                            "type": var.pop('type')
                        },
                        "identifiers": {
                            "genomicHGVSId": var['hgvsid']
                        }
                    }
                # move allele-specific info to the variant, like CSQ annotations
                if 'info' in var:
                    if 'CSQ' in var['info']:
                        if 'molecularAttributes' not in resultset[var['hgvsid']]:
                            compile_molecular_attributes_from_csq(resultset[var['hgvsid']], var['info'].pop('CSQ'))

            # now process the samples into the variations:
            if 'samples' in variant and len(variant['samples']) > 0:
                for k in variant['samples'].keys():
                    sample = variant['samples'][k]
                    # Begin creating a Case Level Data object
                    cld = {
                        'genotype': {
                            'value': sample['GT']
                        }
                    }
                    # check to see that we should be processing the actual sample data:
                    if is_authed:
                        cld['analysisId'] = drs_obj
                        cld['biosampleId'] = k
                    alleles = sample['GT'].split('/')
                    if len(alleles) < 2:
                        alleles = sample['GT'].split('|')
                    # put a copy of this cld in each variation:
                    cld['genotype']['secondaryAlleleIds'] = [resultset[drs_obj][int(alleles[0])], resultset[drs_obj][int(alleles[1])]]
                    if alleles[0] == alleles[1]:
                        cld['genotype']['zygosity'] = {
                            'id': 'GENO:0000136',
                            'label': 'homozygous'
                        }
                        cld['genotype'].pop('secondaryAlleleIds')
                        if alleles[0].isdigit():
                            var = resultset[drs_obj][int(alleles[0])]
                            if 'caseLevelData' not in resultset[var]:
                                resultset[var]['caseLevelData'] = []
                            resultset[var]['caseLevelData'].append(json.loads(json.dumps(cld)))
                    else:
                        if alleles[0] == '0' or alleles[1] == '0':
                            cld['genotype']['zygosity'] = {
                                'id': 'GENO:0000458',
                                'label': 'simple heterozygous'
                            }
                        else:
                            cld['genotype']['zygosity'] = {
                                'id': 'GENO:0000402',
                                'label': 'compound heterozygous'
                            }
                        for a in alleles:
                            if a.isdigit():
                                var = resultset[drs_obj][int(a)]
                                # make a copy cld for the other allele's variant
                                second_cld = json.loads(json.dumps(cld))
                                # this allele should not be in cld's secondaryAlleleIds,
                                # and the second allele should not be in second_cld's secondaryAlleleIds
                                second_cld['genotype']['secondaryAlleleIds'].remove(resultset[drs_obj][int(a)])
                                if 'caseLevelData' not in resultset[var]:
                                    resultset[var]['caseLevelData'] = []
                                resultset[var]['caseLevelData'].append(second_cld)
        resultset.pop(drs_obj)
    final_resultset = []
    # only include variants that are actually seen in the data (not things like ref alleles that are not in any samples)
    for variant in resultset.keys():
        if 'caseLevelData' in resultset[variant] and len(resultset[variant]['caseLevelData']) > 0:
            resultset[variant]['variantInternalId'] = variant
            final_resultset.append(resultset[variant])
    return final_resultset


def compile_variations_from_record(ref="", alt="", chrom="", pos="", reference_genome="hg38"):
    start = int(pos)
    end = int(pos)
    variations = [
        {
            "type": "Allele",
            "location": {
                "interval": {
                    "start": {
                        "value": start - 1, # interbase count, so start is from 0
                        "type": "Number"
                    },
                    "end": {
                        "value": end,
                        "type": "Number"
                    },
                    "type": "SequenceInterval"
                },
                "type": "SequenceLocation",
                "sequence_id": ""
            },
            "state": {
                "type": "LiteralSequenceExpression",
                "sequence": ref
            }
        }
    ]

    # find the correct sequence_id for the chromosome:
    seqid = database.get_refseq_for_chromosome(reference_genome=reference_genome, contig=database.normalize_contig(chrom))
    hgvsid_base = ""
    if seqid is not None:
        variations[0]['location']['sequence_id'] = "refseq:" + seqid
        hgvsid_base = f"{seqid}:g.{start}"

    # alt can be a comma-separated list
    alts = alt.split(',')
    for a in alts:
        # make a copy of the ref variation
        alt_variation = json.loads(json.dumps(variations[0]))
        variations.append(alt_variation)
        if len(ref) == 1 and len(a) == 1: # snp
            alt_variation['state']['sequence'] = a
            alt_variation['hgvsid'] = f"{hgvsid_base}{ref}>{a}"
            continue
        if '<CN' in a:
            # this is a copy number variation
            cn_parse = re.match(r"<CN(\d+)>", a)
            if cn_parse is not None:
                copynum = int(cn_parse.group(1))
                alt_variation['state']['sequence'] = ref * copynum
                alt_variation['hgvsid'] = f"{hgvsid_base}{ref}[{copynum}]"
                continue

        # TODO: process other sorts of sequence changes according to https://varnomen.hgvs.org/recommendations/DNA/variant
        # in the meantime, notate all like delins
        alt_variation['state']['sequence'] = a
        alt_variation['hgvsid'] = f"{hgvsid_base}_{start+len(ref)}delins{a}"
        # raise Exception(f"can't parse alt allele: alt = {a}, ref = {ref}")

    # set the hgvsid of the ref:
    variations[0]['hgvsid'] = f"{hgvsid_base}="
    return variations


def assign_info_to_variations(variant):
    if 'info' not in variant:
        return None
    info_obj = variant['info']
    if 'variations' in variant:
        # assign INFOs that can go to specific variations to their variations
        keys = list(info_obj.keys())
        for k in keys:
            info = info_obj[k]
            if 'Number' in info:
                if info['Number'] == 'R' or info['Number'] == 'A':
                    vals = info['Value']
                    offset = 0
                    if info['Number'] == 'A':
                        offset = 1
                    for i in range(len(vals)):
                        if 'info' not in variant['variations'][i+offset]:
                            variant['variations'][i+offset]['info'] = {}
                        variant['variations'][i+offset]['info'][k] = {
                            'Description': info['Description'],
                            'Value': vals[i]
                        }
                    info_obj.pop(k)
                elif info['Number'] == 'K':
                    # find the variation matching the key:
                    variation_alleles = list(map(lambda x: x['state']['sequence'], variant['variations']))
                    alleles = list(info['Value'].keys())
                    for a in alleles:
                        #index = variation_alleles.index(a)
                        if a == '-': # vep doesn't label alleles for deletions: it's gotta be the alt allele
                            index = 1
                        elif f"{variation_alleles[0]}{a}" in variation_alleles: # vep labels insertions as the allele without the ref
                            index = variation_alleles.index(f"{variation_alleles[0]}{a}")
                        else:
                            if a not in variation_alleles:
                                raise Exception(f"{a} not in {variation_alleles} {info['Value']}")
                            index = variation_alleles.index(a)
                        if 'info' not in variant['variations'][index]:
                            variant['variations'][index]['info'] = {}
                        variant['variations'][index]['info'][k] = {
                            'Description': info['Description'],
                            'Value': info['Value'].pop(a)
                        }
                    info_obj.pop(k)


def compile_molecular_attributes_from_csq(g_variant, csq_list):
    aa_changes = set()
    gene_ids = set()
    mol_effects = set()
    genomic_features = set()
    for csq in csq_list['Value']:
        if 'HGNC_ID' in csq:
            gene_ids.add(csq['HGNC_ID'])
        if 'SYMBOL' in csq:
            gene_ids.add(csq['SYMBOL'])
        if 'Gene' in csq:
            gene_ids.add(csq['Gene'])
        if 'Consequence' in csq:
            for c in csq['Consequence'].split('&'):
                mol_effects.add(c)

    g_variant['molecularAttributes'] = {}
    if len(aa_changes) > 0:
        g_variant['molecularAttributes']['aminoacidChanges'] = list(aa_changes)
    if len(gene_ids) > 0:
        g_variant['molecularAttributes']['geneIds'] = list(gene_ids)
    if len(mol_effects) > 0:
        g_variant['molecularAttributes']['molecularEffects'] = []
        for c in mol_effects:
            g_variant['molecularAttributes']['molecularEffects'].append(get_mol_effect_from_consequence(c))


def get_mol_effect_from_consequence(consequence):
    # table of VEP Consequence values from https://grch37.ensembl.org/info/genome/variation/prediction/predicted_data.html
    csq_values = {
        "transcript_ablation": "SO:0001893",
        "splice_acceptor_variant": "SO:0001574",
        "splice_donor_variant": "SO:0001575",
        "stop_gained": "SO:0001587",
        "frameshift_variant": "SO:0001589",
        "stop_lost": "SO:0001578",
        "start_lost": "SO:0002012",
        "transcript_amplification": "SO:0001889",
        "inframe_insertion": "SO:0001821",
        "inframe_deletion": "SO:0001822",
        "missense_variant": "SO:0001583",
        "protein_altering_variant": "SO:0001818",
        "splice_region_variant": "SO:0001630",
        "incomplete_terminal_codon_variant": "SO:0001626",
        "start_retained_variant": "SO:0002019",
        "stop_retained_variant": "SO:0001567",
        "synonymous_variant": "SO:0001819",
        "coding_sequence_variant": "SO:0001580",
        "mature_miRNA_variant": "SO:0001620",
        "5_prime_UTR_variant": "SO:0001623",
        "3_prime_UTR_variant": "SO:0001624",
        "non_coding_transcript_exon_variant": "SO:0001792",
        "intron_variant": "SO:0001627",
        "NMD_transcript_variant": "SO:0001621",
        "non_coding_transcript_variant": "SO:0001619",
        "upstream_gene_variant": "SO:0001631",
        "downstream_gene_variant": "SO:0001632",
        "TFBS_ablation": "SO:0001895",
        "TFBS_amplification": "SO:0001892",
        "TF_binding_site_variant": "SO:0001782",
        "regulatory_region_ablation": "SO:0001894",
        "regulatory_region_amplification": "SO:0001891",
        "feature_elongation": "SO:0001907",
        "regulatory_region_variant": "SO:0001566",
        "feature_truncation": "SO:0001906",
        "intergenic_variant": "SO:0001628"
    }
    if consequence in csq_values:
        return {
            "id": csq_values[consequence],
            "label": consequence
        }
    return None

