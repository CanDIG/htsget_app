import os
import re
import tempfile
from flask import send_file, Flask
from urllib.parse import urlencode, urlparse, parse_qs
import database
import authz
from config import CHUNK_SIZE, HTSGET_URL, BUCKET_SIZE, PORT, INDEXING_PATH, INDEXING_SWITCH_FILE
from markupsafe import escape
import connexion
import variants
import indexing
from pathlib import Path
from candigv2_logging.logging import CanDIGLogger
from pysam import VariantFile, AlignmentFile, FastxFile
import requests
from authx.auth import create_service_token


logger = CanDIGLogger(__file__)


app = Flask(__name__)

# Endpoints
def get_read_service_info():
    return {
        "id": "org.candig.htsget",
        "name": "CanDIG htsget service",
        "type": {
            "group": "org.ga4gh",
            "artifact": "htsget",
            "version": "v1.3.0"
        },
        "description": "An htsget-compliant server for CanDIG genomic data",
        "organization": {
            "name": "CanDIG",
            "url": "https://www.distributedgenomics.ca"
        },
        "version": "1.0.0",
        "htsget": {
            "datatype": "reads",
            "formats": ["BAM", "CRAM", "SAM"],
            "fieldsParameterEffective": False,
            "tagsParametersEffective": False
        }
    }


def get_variant_service_info():
    return {
        "id": "org.candig.htsget",
        "name": "CanDIG htsget service",
        "type": {
            "group": "org.ga4gh",
            "artifact": "htsget",
            "version": "v1.3.0"
        },
        "description": "An htsget-compliant server for CanDIG genomic data",
        "organization": {
            "name": "CanDIG",
            "url": "https://www.distributedgenomics.ca"
        },
        "version": "1.0.0",
        "htsget": {
            "datatype": "variants",
            "formats": ["VCF", "BCF"],
            "fieldsParameterEffective": False,
            "tagsParametersEffective": False
        }
    }


def indexer_status():
    if os.path.isfile(INDEXING_SWITCH_FILE):
        return {"status": "ON"}, 200
    return {"status": "OFF"}, 200


def indexer_switch(status=None):
    if not authz.has_full_authz(connexion.request):
        return {"message": "User is not authorized to switch indexer"}, 403
    if status == "ON":
        try:
            open(INDEXING_SWITCH_FILE, "x")
            return {"status": "ON"}, 200
        except FileExistsError:
            pass
        except Exception as e:
            return {"error": f"indexer switch error {status}:  {type(e)} {str(e)}"}, 500
    if status == "OFF":
        try:
            if os.path.isfile(INDEXING_SWITCH_FILE):
                os.remove(INDEXING_SWITCH_FILE)
            return {"status": "OFF"}, 200
        except Exception as e:
            return {"error": f"indexer switch error {status}: {type(e)} {str(e)}"}, 500


@app.route('/reads/<path:id_>')
def get_reads(id_=None, reference_name=None, start=None, end=None, class_=None, format_=None):
    if id_ is not None:
        return _get_urls("read", escape(id_), reference_name, start, end, class_)
    else:
        return None, 404
    return None, auth_code


@app.route('/reads/data/<path:id_>')
def get_reads_data(id_, reference_name=None, format_="bam", start=None, end=None, class_="body"):
    if id_ is not None:
        return _get_data(escape(id_), reference_name, start, end, class_, format_)
    else:
        return None, 404
    return None, auth_code


@app.route('/variants/<path:id_>')
def get_variants(id_=None, reference_name=None, start=None, end=None, class_=None, format_=None):
    if id_ is not None:
        return _get_urls("variant", escape(id_), reference_name, start, end, class_)
    else:
        return None, 404
    return None, auth_code


@app.route('/variants/data/<path:id_>')
def get_variants_data(id_, reference_name=None, format_="VCF", start=None, end=None, class_=None):
    if id_ is not None:
        if format_ == "VCF-JSON":
            return variants.parse_vcf_file(id_, reference_name=reference_name, start=start, end=end)
        res = _get_data(escape(id_), reference_name, start, end, class_, format_)
        return res
    else:
        return None, 404
    return None, auth_code


@app.route('/<path:id_>/index')
def index_analysis(id_=None, force=False, genome='hg38'):
    if not authz.has_full_authz(connexion.request):
        return {"message": "User is not authorized to index analyses"}, 403
    if id_ is not None:
        headers = {
            "X-Service-Token": create_service_token()
        }

        # check that there is a database drs object for this:
        drs_obj = _describe_drs_object(id_)
        if drs_obj is None:
            return {"message": f"No DRS object exists with ID {id_}"}, 404
        program = ""
        if "program" in drs_obj:
            program = drs_obj['program']
        params = {"id": id_, "reference_genome": genome}
        try:
            if drs_obj['type'] == 'variant':
                varfile = database.create_variantfile(params)
                if varfile is not None:
                    if varfile['indexed'] == 1 and not force:
                        # make sure that the index tags are correct in the drs_object
                        if "metadata" not in drs_obj["drs_obj"]:
                            drs_obj["drs_obj"]["metadata"] = {}
                        if "indexed" not in drs_obj["drs_obj"]["metadata"]:
                            drs_obj["drs_obj"]["metadata"]["indexed"] = 1
                            resp = requests.post(url=f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/objects", headers=headers, json=drs_obj["drs_obj"])
                        return varfile, 200
            Path(f"{INDEXING_PATH}/{program}~{id_}").touch()
            return None, 200
        except Exception as e:
            return {"message": f"INDEXING ERROR {type(e)} {str(e)}"}, 500
    else:
        return None, 404


@app.route('/<path:id_>/verify')
def verify_analysis_drs_object(id_):
    try:
        _verify_analysis_drs_object(id_)
    except Exception as e:
        return {"result": False, "message": str(e)}, 200
    return {"result": True}, 200

@app.route('/genes')
def list_genes(type="gene_name"):
    genes = database.list_refseqs()
    results = set()
    if genes is None:
        return {"results": []}, 200
    for gene in genes:
        results.add(gene[type])
    results = list(results)
    results.sort()
    return {"results": results}, 200


@app.route('/transcripts')
def list_transcripts():
    return list_genes(type="transcript_name")


@app.route('/genes/<path:id_>')
def get_matching_genes(id_=None, type="gene_name"):
    genes = database.search_refseqs(id_.upper(), type)
    results = []
    if genes is None:
        return {"results": results}, 200
    count = 0
    curr_gene = ""
    for gene in genes:
        if gene[type] != curr_gene:
            curr_gene = gene[type]
            count += 1
            if count > 5:
                break
            res = {
                "gene_name": gene['gene_name'],
                "transcript_name": gene['transcript_name'],
                "regions": []
            }
            results.append(res)
        if database.normalize_contig(gene['contig']) is not None:
            res['regions'].append({
                'reference_genome': gene['reference_genome'],
                'region': {
                    'referenceName': gene['contig'],
                    'start': gene['start'],
                    'end': gene['end']
                }
            })
    return {"results": results}, 200


@app.route('/transcripts/<path:id_>')
def get_matching_transcripts(id_=None):
    return get_matching_genes(id_=id_, type="transcript_name")


@app.route('/biosamples/<path:id_>')
def get_biosample(id_=None):
    if not authz.has_full_authz(connexion.request):
        return {"message": "User is not authorized to get biosamples"}, 403
    result, status_code = _get_biosample(id_)
    if status_code == 200:
        return result, 200
    return {"message": f"Could not get biosample {id_}: {result}"}, status_code


async def get_multiple_biosamples():
    if not authz.has_full_authz(connexion.request):
        return {"message": "User is not authorized to get biosamples"}, 403
    req = await connexion.request.json()
    if "biosamples" in req:
        return _get_biosamples(req["biosamples"]), 200
    return _get_biosamples(None), 200

def get_program_biosamples(program=None):
    if not authz.has_full_authz(connexion.request):
        return {"message": "User is not authorized to get biosamples"}, 403
    biosamples = _get_biosamples(None, program=program)
    if len(biosamples) > 0:
        return biosamples, 200
    return {"message": f"No biosamples found for {program}"}, 404


# This is specific to our particular use case: a DRS object that represents a
# particular experiment can have a variant or read file and an associated index file.
# We need to query DRS to get the bundling object, which should contain links to
# two contents objects.
def get_pysam_obj(object_id, headers=None):
    result = {'status_code': 200}
    index_path = None
    main_path = None

    if headers is None:
        headers = connexion.request.headers
    drs_obj = _describe_drs_object(object_id, headers=headers)
    if drs_obj is None or 'message' in drs_obj:
        return { "message": f"{object_id} not found", "status_code": 404}
    if 'index' in drs_obj:
        resp = requests.get(url=f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/objects/{drs_obj['index']}", headers=headers)
        if resp.status_code == 200:
            index_path = _get_file_path(resp.json())
    result['type'] = drs_obj['type']
    resp = requests.get(url=f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/objects/{drs_obj['main']}", headers=headers)
    if resp.status_code == 200:
        main_path = _get_file_path(resp.json())

    if "samples" in drs_obj:
        result['experiments'] = drs_obj['samples']
    elif "experiments" in drs_obj:
        result['experiments'] = drs_obj['experiments']

    if main_path is not None:
        if drs_obj['type'] == "fastx":
            try:
                result['file_format'] = drs_obj['format']
                result['file'] = FastxFile(main_path)
            except Exception as e:
                return { "message": str(e), "status_code": 500, "method": f"get_pysam_obj({object_id})"}
        elif index_path is not None:
            ## this is for migration: experiments used to be samples
            try:
                result['file_format'] = drs_obj['format']
                if drs_obj['type'] == 'read':
                    result['file'] = AlignmentFile(main_path, index_filename=index_path)
                else:
                    result['file'] = VariantFile(main_path, index_filename=index_path)
            except Exception as e:
                return { "message": str(e), "status_code": 500, "method": f"get_pysam_obj({object_id})"}
        else:
            return {"status_code": 404, "message": "could not locate index or analysis file"}
    else:
        return {"status_code": 404, "message": "could not locate main file"}
    return result


def _get_biosamples(biosamples, program=None):
    result = []
    headers = {
        "X-Service-Token": create_service_token()
    }
    if biosamples is None:
        resp = requests.post(f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/biosamples", headers=headers, json={})
    else:
        resp = requests.post(f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/biosamples", headers=headers, json={"submitter_sample_ids": biosamples})
    if resp.status_code == 200:
        biosamples_by_program = {}
        for res in resp.json():
            if res["program"] not in biosamples_by_program:
                biosamples_by_program[res["program"]] = []
            biosamples_by_program[res["program"]].append(res)
        if program is not None:
            if program in biosamples_by_program:
                return biosamples_by_program[program]
            return result
        for program in biosamples_by_program.keys():
            result.extend(biosamples_by_program[program])
    return result


def _get_biosample(id_=None):
    headers = {
        "X-Service-Token": create_service_token()
    }
    resp = requests.post(f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/biosamples", headers=headers, json={"submitter_sample_ids": [id_]})

    if resp.status_code == 200:
        if len(resp.json()) == 0:
            return f"{id_} is not an Biosample", 404
        return resp.json().pop(), 200
    return resp.text, resp.status_code


def _get_htsget_url(id, reference_name, slice_start, slice_end, file_type, data=True):
    """
    Creates single slice for a region in a file. Returns an HTSGetURL object.

    :param id: ID of the file
    :param reference_name: The Chromosome number
    :param slice_start: Starting index of a slice
    :param slice_end: Ending index of a slice
    :param file_type: "read" or "variant"
    :param data: if this is a data url or just a ticket url
    """
    params = {}
    if data:
        params['class'] = 'body'
    if reference_name is not None:
        params['referenceName'] = reference_name
        if slice_start is not None:
            params['start'] = slice_start
        if slice_end is not None:
            params['end'] = slice_end
    encoded_params = urlencode(params)
    url = f"{_get_base_url(file_type, id, data=data)}"
    if len(params.keys()) > 0:
        url += f"?{encoded_params}"
    return {'url': url}


def _get_htsget_urls(id, reference_name, start, end, file_type):
    """
    Returns array of slices of URLs

    :param chunk_size: The size of the chunk or slice
                      ( e.g. 10,000,000 pieces of data )
    :param id: ID of the file
    :param reference_name: Chromosome Number
    :param start: Desired starting index of a file
    :param end: Desired ending index of a file
    :param file_type: "read" or "variant"
    """
    urls = []
    if start is None:
        start = 0
    if end is None:
        end = -1

    # start pulling buckets: when we reach chunk size, make another chunk
    buckets = database.get_variant_count_for_variantfile({"id": id, "referenceName": reference_name, "start": start, "end": end})
    # return buckets
    chunks = [{'count': 0, 'start': start, 'end': 0}]
    while len(buckets) > 0:
        curr_bucket = buckets.pop(0)
        curr_chunk = chunks.pop()
        # if the curr_chunk size is smaller than chunk size, we're still adding to it
        if curr_chunk['count'] <= CHUNK_SIZE:
            curr_chunk['count'] += curr_bucket['count']
            curr_chunk['end'] = curr_bucket['pos_bucket']
            chunks.append(curr_chunk)
        else:
            # new chunk: append old chunk, then start new
            chunks.append(curr_chunk)
            chunks.append({'count': 0, 'start': curr_chunk['end']+1, 'end': curr_chunk['end']+1})
    # for the last chunk, use the actual end requested:
    if end != -1:
        chunks[-1]['end'] = end
    else:
        chunks[-1]['end'] += BUCKET_SIZE
    # return chunks
    for i in range(0,len(chunks)):
        slice_start = chunks[i]['start']
        slice_end = chunks[i]['end']
        url = _get_htsget_url(id, reference_name, slice_start, slice_end, file_type)
        url['class'] = 'body'
        urls.append(url)
    return urls


def _get_data(id_, reference_name=None, start=None, end=None, class_=None, format_="VCF"):
    """
    Returns the specified file:

    :param id: ID of the file ( e.g. id=HG02102 for file HG02102.vcf.gz )
    :param reference_name: Chromosome or contig name
    :param format: Format of output (e.g. vcf, bcf)
    :param start: Position index to begin at (0-based inclusive)
    :param end: Position index to end at (0-based exclusive)
    """
    if end is not None and end != -1 and end < start:
        response = {
            "detail": "End index cannot be smaller than start index",
            "status": 400,
            "title": "Bad Request",
            "type": "about:blank"
        }
        return "end cannot be less than start", 400

    if reference_name == "None":
        reference_name = None

    if end == -1:
        end = None
    if start == 0:
        start = None

    format_ = format_.lower()
    file_type = "variant"
    if format_ in ["bam", "sam", "cram"]:
        file_type = "alignment"

    write_mode = "w"
    if format_ in ["bcf", "bam"]:
        write_mode = "wb"
    elif format_ in ["cram"]:
        write_mode = "wc"

    file_in = None
    file_name = f"{id_}.{format_}"

    # get a file and index from drs, based on the id_
    gen_obj = get_pysam_obj(id_)
    if gen_obj is not None:
        if "message" in gen_obj:
            return gen_obj['message'], gen_obj['status_code']
        file_in = gen_obj["file"]
        ntf = tempfile.NamedTemporaryFile(prefix='htsget', suffix=format_,
                                 mode='wb', delete=False)
        if class_ is None or class_ == "header":
            ntf.write(str(file_in.header).encode('utf-8'))

        if class_ is None or class_ == "body":
            ref_name = None
            if reference_name is not None:
                # there will have to be an update when we figure out how to index read files
                try:
                    ref_name = database.get_contig_name_in_variantfile({'refname': reference_name, 'variantfile_id': id_})
                except:
                    ref_name = None
                if ref_name is None:
                    ref_name = reference_name
            try:
                fetch = file_in.fetch(contig=ref_name, start=start, end=end)
                for rec in fetch:
                    ntf.write(str(rec).encode('utf-8'))
            except ValueError as e:
                return {"message": str(e)}, 400

        file_in.close()
        ntf.close()

        # Send the temporary file as the response
        response = send_file(path_or_file=ntf.name,
                             download_name=file_name, as_attachment=True)
        response.headers["x-filename"] = file_name
        response.headers["Access-Control-Expose-Headers"] = 'x-filename'
        os.remove(ntf.name)
        return response, 200
    return { "message": "no object matching id found" }, 404


def _get_base_url(file_type, id, data=False, testing=False):
    """
    Returns the base URL

    :param file_type: "read" or "variant"
    :param id: ID of a file
    :param data: if this is a data url or just a ticket url
    :param testing: if this is for testing
    """
    url = HTSGET_URL
    if data:
        return f"{url}/htsget/v1/{file_type}s/data/{id}"
    return f"{url}/htsget/v1/{file_type}s/{id}"


def _get_urls(file_type, id, reference_name=None, start=None, end=None, _class=None, headers=None):
    """
    Searches for file from ID and Return URLS for Read/Variant

    :param file_type: "read" or "variant"
    :param id: ID of a file
    :param reference_name: Chromosome Number
    :param start: Desired starting index of the file
    :param end: Desired ending index of the file
    """
    if end is not None and start is not None:
        if end < start:
            response = {
                "detail": "End index cannot be smaller than start index",
                "status": 400,
                "title": "Bad Request",
                "type": "about:blank"
            }
            return {"message": "end cannot be less than start"}, 400

    if reference_name == "None":
        reference_name = None

    if file_type not in ["variant", "read"]:
        raise ValueError("File type must be 'variant' or 'read'")

    if headers is None:
        headers = connexion.request.headers
    drs_obj = _describe_drs_object(id, headers=headers)
    if drs_obj is not None and "status_code" not in drs_obj:
        if "format" not in drs_obj:
            raise Exception(f"no format: {drs_obj}")
        if "error" in drs_obj:
            return drs_obj['error'], drs_obj['status_code']
        response = {
            'htsget': {
                'format': drs_obj["format"],
                'urls': [{"url": f"{_get_base_url(file_type, id, data=True)}?class=header", "class": "header"}]
            }
        }
        if _class == "header":
            return response, 200

        file_in = drs_obj["main"]
        index = drs_obj["index"]
        response['htsget']['urls'].extend(_get_htsget_urls(id, reference_name, start, end, file_type))
        return response, 200
    return drs_obj["message"], drs_obj["status_code"]


def _verify_analysis_drs_object(id_):
    # get the listed experiments that the AnalysisDrsObject says should be in the file
    gen_drs_obj = _describe_drs_object(id_)
    if gen_drs_obj is None:
        raise Exception(f"Could not find object {id_}")
    if "status_code" in gen_drs_obj:
        raise Exception(f"Error getting drs object: {gen_drs_obj}")
    drs_experiments = set(gen_drs_obj['experiments'].keys())
    if 'type' not in gen_drs_obj:
        raise Exception(f"Object {id_} should be a AnalysisDrsObject, but does not link to a variant or read file")
    file_type = gen_drs_obj['type']

    # get the experiments that are in the linked files
    gen_obj = get_pysam_obj(id_)
    if gen_obj is None:
        raise Exception(f"No analysis object with id {id_} exists")
    if "message" in gen_obj:
        raise Exception(f"{gen_obj['message']}")
    if file_type == "variant":
        # for variant files, we can test whether the linked file is readable by querying it for its experiments.
        file_samples = set(gen_obj['file'].header.samples)
        test = drs_experiments.difference(file_samples)
        # the AnalysisDrsObject's listed ContentsObjects > ExperimentDrsObjects should match the samples in the VCF file.
        if len(test) > 0:
            raise Exception(f"AnalysisDrsObject {id_} lists experiments {test} that are not in the linked analysis file")
        # variant files should have an analysis_date
        if database.get_analysis_date_from_headers(str(gen_obj['file'].header).split('\n')) is None:
            raise Exception(f"AnalysisDrsObject {id_} does not have any associated analysis date")
    elif file_type == "fastx":
        # pysam doesn't seem to throw exceptions if you try to create a fastxfile from something not fastx, so we'll have to try to grab an entry. Apparently it will always iterate at least once, so a valid entry will have more than one entry in it.
        num_entries = 0
        for entry in gen_obj['file']:
            num_entries = num_entries + 1
        if num_entries <= 1:
            raise Exception(f"RunDrsObject {id_} does not seem a valid fastx file")
    else:
        # for read files, we can test whether the linked file is readable by checking for references in the header.
        try:
            if len(gen_obj['file'].header.references) == 0:
                raise Exception(f"AnalysisDrsObject {id_} links to a read file with no reference sequences")
        except Exception as e:
            raise Exception(f"AnalysisDrsObject {id_} links to a read file that could not be read: {str(e)}")
        if len(drs_experiments) > 1:
            raise Exception(f"AnalysisDrsObject {id_} lists multiple experiments, but only one can be in the read file")
    return None


# describe an htsget DRS object, but don't open it
def _describe_drs_object(object_id, headers=None):
    if headers is None:
        headers = connexion.request.headers
    resp = requests.get(url=f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/objects/{object_id}", headers=headers)
    if resp.status_code == 200:
        drs_obj = resp.json()

        if drs_obj is None:
            return None

        if drs_obj["description"] not in ["reference_alignment", "sequence_variation", "raw_reads"]:
            return {"message": f"drs object {object_id} does not represent an htsget object", "status_code": 404}

        result = {
            "name": object_id,
            "program": drs_obj["program"],
            "drs_obj": drs_obj
        }
        # drs_obj should have a main contents, index contents, and experiment contents
        if "contents" in drs_obj:
            for contents in drs_obj["contents"]:
                # get each drs object (should be the analysis file and its index)
                # if sub_obj.name matches an index file regex, it's an index file
                index_match = re.fullmatch(r'.+\.(...*i)$', contents["name"])

                # if sub_obj.name matches a bam/sam/cram file regex, it's a read file
                read_match = re.fullmatch(r'.+\.(.+?am)$', contents["name"])

                # if sub_obj.name matches a vcf/bcf file regex, it's a variant file
                variant_match = re.fullmatch(r'.+\.(.cf)(\.gz)*$', contents["name"])

                # if sub_obj.name matches a fastx file regex, it's a fastx file
                fastx_match = re.fullmatch(r'.+\.(f[aq](st.)*)(\.gz)*$', contents["name"])

                if read_match is not None:
                    result['format'] = read_match.group(1).upper()
                    result['type'] = "read"
                    result['main'] = contents['name']
                elif variant_match is not None:
                    result['format'] = variant_match.group(1).upper()
                    result['type'] = "variant"
                    result['main'] = contents['name']
                elif index_match is not None:
                    result['index'] = contents['name']
                elif fastx_match is not None:
                    result['format'] = fastx_match.group(1).upper()
                    if result['format'] == 'fa':
                        result['format'] = 'fasta'
                    elif result['format'] == 'fq':
                        result['format'] == 'fastq'
                    result['type'] = "fastx"
                    result['main'] = contents['name']
                else:
                    ## this is for migration: experiments used to be samples
                    if "samples" in result:
                        result["experiments"] = result["samples"]
                    if "experiments" not in result:
                        result['experiments'] = {}
                    result['experiments'][contents['id']] = contents['name']
    else:
        return {"message": resp.text, "status_code": resp.status_code}
    if 'type' not in result:
        return {"message": f"drs object {object_id} does not represent an htsget object", "status_code": 404}
    return result


def _get_file_path(drs_file_obj):
    for method in drs_file_obj["access_methods"]:
        if "access_id" in method and method["access_id"] != "":
            # we need to go to the access endpoint to get the url and file
            headers = {
                "X-Service-Token": create_service_token()
            }
            url_obj, status_code = _get_access_url(method["access_id"])
            if status_code < 300:
                return url_obj["url"]
        elif method["type"] == "file":
            # the access_url has all the info we need
            url_pieces = urlparse(method["access_url"]["url"])
            if url_pieces.scheme == "file":
                if url_pieces.netloc == "" or url_pieces.netloc == "localhost":
                    result = os.path.abspath(url_pieces.path)
                    if os.path.exists(result):
                        return result
    return None

def _get_access_url(access_id):
    logger.debug(f"looking for url {access_id}")
    id_parse = re.match(r"((https*:\/\/)*.+?)\/(.+?)\/(.+?)(\?(.+))*$", access_id)
    if id_parse is not None:
        endpoint = id_parse.group(1)
        bucket = id_parse.group(3)
        object_name = id_parse.group(4)
        url = None
        if id_parse.group(5) is None:
            url, status_code = authz.get_s3_url(s3_endpoint=endpoint, bucket=bucket, object_id=object_name)
        else:
            keys = parse_qs(id_parse.group(6))
            access = None
            secret = None
            public = False
            if 'access' in keys:
                access = keys['access'].pop()
            if 'secret' in keys:
                secret = keys['secret'].pop()
            if 'public' in keys:
                public = True
            url, status_code = authz.get_s3_url(s3_endpoint=endpoint, bucket=bucket, object_id=object_name, access_key=access, secret_key=secret, public=public)
        if status_code == 200:
            return url, status_code
        return url, 500
    else:
        return {"message": f"Malformed access_id {access_id}: should be in the form endpoint/bucket/item", "method": "_get_access_url"}, 400
