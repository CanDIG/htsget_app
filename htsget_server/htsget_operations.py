import os
import tempfile
from flask import request, send_file, Flask
from urllib.parse import urlencode
import drs_operations
import database
import authz
from config import CHUNK_SIZE, HTSGET_URL, BUCKET_SIZE, PORT, INDEXING_PATH
from markupsafe import escape
import connexion
import variants
import indexing
from pathlib import Path


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


@app.route('/reads/<path:id_>')
def get_reads(id_=None, reference_name=None, start=None, end=None, class_=None, format_=None):
    if id_ is not None:
        auth_code = authz.is_authed(escape(id_), request)
        if auth_code == 200:
            return _get_urls("read", escape(id_), reference_name, start, end, class_)
    else:
        return None, 404
    return None, auth_code


@app.route('/reads/data/<path:id_>')
def get_reads_data(id_, reference_name=None, format_="bam", start=None, end=None, class_="body"):
    if id_ is not None:
        auth_code = authz.is_authed(escape(id_), request)
        if auth_code == 200:
            return _get_data(escape(id_), reference_name, start, end, class_, format_)
    else:
        return None, 404
    return None, auth_code


@app.route('/variants/<path:id_>')
def get_variants(id_=None, reference_name=None, start=None, end=None, class_=None, format_=None):
    if id_ is not None:
        auth_code = authz.is_authed(escape(id_), request)
        if auth_code == 200:
            return _get_urls("variant", escape(id_), reference_name, start, end, class_)
    else:
        return None, 404
    return None, auth_code


@app.route('/variants/data/<path:id_>')
def get_variants_data(id_, reference_name=None, format_="VCF", start=None, end=None, class_=None):
    if id_ is not None:
        auth_code = authz.is_authed(escape(id_), request)
        if auth_code == 200:
            if format_ == "VCF-JSON":
                return variants.parse_vcf_file(id_, reference_name=reference_name, start=start, end=end)
            return _get_data(escape(id_), reference_name, start, end, class_, format_)
    else:
        return None, 404
    return None, auth_code


@app.route('/variants/<path:id_>/index')
def index_variants(id_=None, force=False, genome='hg38', genomic_id=None):
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to index variants"}, 403
    if id_ is not None:
        params = {"id": id_, "reference_genome": genome}
        if genomic_id is not None:
            params["genomic_id"] = genomic_id
        try:
            varfile = database.create_variantfile(params)
            if varfile is not None:
                if varfile['indexed'] == 1 and not force:
                    return varfile, 200
            Path(f"{INDEXING_PATH}/{id_}").touch()
            return None, 200
        except Exception as e:
            return {"message": str(e)}, 500
    else:
        return None, 404


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


@app.route('/samples/<path:id_>')
def get_sample(id_=None):
    result = {
        "sample_id": id_,
        "genomes": [],
        "transcriptomes": []
    }

    # Get the SampleDrsObject. It will have a contents array of GenomicContentsObjects > GenomicDrsObjects.
    # Each of those GenomicDrsObjects will have a description that is either 'wgs' or 'wts'.
    sample_drs_obj, result_code = drs_operations.get_object(id_)
    if result_code == 200 and "contents" in sample_drs_obj and sample_drs_obj["description"] == "sample":
        for contents_obj in sample_drs_obj["contents"]:
            drs_obj = database.get_drs_object(contents_obj["id"])
            if drs_obj is not None:
                if drs_obj["description"] == "wgs":
                    result["genomes"].append(drs_obj["id"])
                elif drs_obj["description"] == "wts":
                    result["transcriptomes"].append(drs_obj["id"])
        return result, 200
    return {"message": f"Could not find sample {id_}"}, 404


def get_samples():
    req = connexion.request.json
    result = []
    for sample in req["samples"]:
        res, status_code = get_sample(sample)
        if status_code == 200:
            result.append(res)
    return result, 200


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
    gen_obj = drs_operations._get_genomic_obj(id_)
    if gen_obj is not None:
        if "message" in gen_obj:
            return {"message": gen_obj['message']}, gen_obj['status_code']
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
    if authz.is_testing(request):
        url = os.getenv("TESTENV_URL", f"http://localhost:{PORT}")
    if data:
        return f"{url}/htsget/v1/{file_type}s/data/{id}"
    return f"{url}/htsget/v1/{file_type}s/{id}"


def _get_urls(file_type, id, reference_name=None, start=None, end=None, _class=None):
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

    drs_obj = drs_operations._describe_drs_object(id)
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
    return {"message": f"No {file_type} found for id: {id}, try using the other endpoint"}, 404


