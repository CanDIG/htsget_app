import os
import re
import tempfile
import requests
from flask import request, send_file, Flask
from pysam import VariantFile, AlignmentFile
from urllib.parse import urlparse, urlencode
import drs_operations
import database
import authz
import json
from config import CHUNK_SIZE, HTSGET_URL, BUCKET_SIZE, PORT
from markupsafe import escape
import connexion


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
def get_variants_data(id_, reference_name=None, format_="VCF", start=None, end=None, class_="body"):
    if id_ is not None:
        auth_code = authz.is_authed(escape(id_), request)
        if auth_code == 200:
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
        varfile = database.create_variantfile(params)
        if varfile is not None:
            if varfile['indexed'] == 1 and not force:
                return varfile, 200
        gen_obj = _get_genomic_obj(id_)
        if gen_obj is None:
            return {"message": f"No variant with id {id_} exists"}, 404
        if "error" in gen_obj:
            return {"message": gen_obj['error']}, 500
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
            varfile['pos'] = res
            database.mark_variantfile_as_indexed(id_)
        return varfile, 200
    else:
        return None, 404


@app.route('/variants/search')
def search_variants():
    req = connexion.request
    # for now, only work with one region:
    ref_name = None
    start = None
    end = None
    if 'regions' in req.json:
        if len(req.json['regions']) > 1:
            return {"message": "Only one region at a time is searchable for now."}, 400
        region = req.json['regions'][0]
        ref_name = database.normalize_contig(region['referenceName'])
        if 'start' in region:
            start = region['start'] - 1
            if start < 0:
                start = 0
        if 'end' in region:
            end = region['end']
    searchresult = database.search(req.json)
    result = {'results': []}
    for i in range(len(searchresult['drs_object_ids'])):
        drs_obj_id = searchresult['drs_object_ids'][i]
        count = searchresult['variantcount'][i]
        auth_code = authz.is_authed(drs_obj_id, connexion.request)
        if auth_code == 200:
            htsget_obj = {
                'format': 'vcf',
                'urls': []
            }
            htsget_obj['urls'].append(_get_base_url("variant", drs_obj_id, data=False))
            htsget_obj['id'] = drs_obj_id
            htsget_obj['variantcount'] = count
            htsget_obj['genomic_id'] = database.get_variantfile(drs_obj_id)['genomic_id']
            htsget_obj['samples'] = database.get_samples_in_drs_objects({'drs_object_ids': [drs_obj_id]})
            htsget_obj['reference_genome'] = searchresult['reference_genome'][i]
            result['results'].append(htsget_obj)
    # This is a good coarse search result, but what if the region is smaller than a bucket?
    # We should actually grab all of the data from the drs_objects in question and count.
    if end is not None and start is not None and (end - start <= BUCKET_SIZE):
        fine_results = []
        for obj in result['results']:
            gen_obj = _get_genomic_obj(obj['id'])
            orig_ref_name = database.get_contig_name_in_variantfile({'refname': ref_name, 'variantfile_id': obj['id']})
            try:
                actual = gen_obj['file'].fetch(contig=orig_ref_name, start=start, end=end)
            except Exception as e:
                return {"message": str(e)}, 500
            actual_count = sum(1 for _ in actual)
            if (actual_count > 0):
                obj['variantcount'] = actual_count
                fine_results.append(obj)
        result['results'] = fine_results

    auth_code = 200
    return result, auth_code


# https://rest.ensembl.org/map/human/GRCh37/X:1000000..1000100:1/GRCh38?content-type=application/json
# https://rest.ensembl.org/xrefs/symbol/homo_sapiens/BRCA2?content-type=application/json

def _create_slice(arr, id, reference_name, slice_start, slice_end, file_type):
    """
    Creates slice and appends it to array of urls

    :param arr: The array to store urls
    :param id: ID of the file
    :param reference_name: The Chromosome number
    :param slice_start: Starting index of a slice
    :param slice_end: Ending index of a slice
    """
    params = {}
    if reference_name is not None:
        params['referenceName'] = reference_name
        if slice_start is not None:
            params['start'] = slice_start
        if slice_end is not None:
            params['end'] = slice_end
    encoded_params = urlencode(params)
    url = f"{_get_base_url(file_type, id, data=True)}"
    if len(params.keys()) > 0:
        url += f"?{encoded_params}"
    arr.append({'url': url, })


def _create_slices(chunk_size, id, reference_name, start, end, file_type):
    """
    Returns array of slices of URLs

    :param chunk_size: The size of the chunk or slice
                      ( e.g. 10,000,000 pieces of data )
    :param id: ID of the file
    :param reference_name: Chromosome Number
    :param start: Desired starting index of a file
    :param end: Desired ending index of a file
    """
    urls = []

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
    chunks[-1]['end'] = end
    # return chunks
    for i in range(0,len(chunks)):
        slice_start = chunks[i]['start']
        slice_end = chunks[i]['end']
        _create_slice(urls, id, reference_name, slice_start, slice_end, file_type)
    return urls


def _get_data(id_, reference_name=None, start=None, end=None, class_="body", format_="VCF"):
    # start = 17148269, end = 17157211, reference_name = 21
    """
    Returns the specified file:

    :param id: ID of the file ( e.g. id=HG02102 for file HG02102.vcf.gz )
    :param reference_name: Chromosome or contig name
    :param format: Format of output (e.g. vcf, bcf)
    :param start: Position index to begin at (1-based inclusive)
    :param end: Position index to end at (1-based inclusive)
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
    gen_obj = _get_genomic_obj(id_)
    if gen_obj is not None:
        if "error" in gen_obj:
            return gen_obj['error'], gen_obj['status_code']
        file_in = gen_obj["file"]
        ntf = tempfile.NamedTemporaryFile(prefix='htsget', suffix=format_,
                                 mode='wb', delete=False)
        if file_type == "variant":
            file_out = VariantFile(ntf, mode=write_mode, header=file_in.header)
        else:
            file_out = AlignmentFile(ntf, mode=write_mode, header=file_in.header)
        if class_ != "header":
            ref_name = None
            if reference_name is not None:
                ref_name = database.get_contig_name_in_variantfile({'refname': reference_name, 'variantfile_id': id_})
            try:
                fetch = file_in.fetch(contig=ref_name, start=start, end=end)
            except ValueError as e:
                return {"error": str(e)}, 400

            for rec in fetch:
                file_out.write(rec)

        file_in.close()
        file_out.close()

        # Send the temporary file as the response
        response = send_file(path_or_file=ntf.name,
                             download_name=file_name, as_attachment=True)
        response.headers["x-filename"] = file_name
        response.headers["Access-Control-Expose-Headers"] = 'x-filename'
        os.remove(ntf.name)
        return response, 200
    return { "message": "no object matching id found" }, 404


def _get_base_url(file_type, id, data=False, testing=False):
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
            return "end cannot be less than start", 400

    if reference_name == "None":
        reference_name = None

    if file_type not in ["variant", "read"]:
        raise ValueError("File type must be 'variant' or 'read'")

    drs_obj = _describe_drs_object(id)
    if drs_obj is not None:
        if "error" in drs_obj:
            return drs_obj['error'], drs_obj['status_code']
        if _class == "header":
            urls = [{"url": f"{_get_base_url(file_type, id, data=True)}?class=header",
            "class": "header"}]
        else:
            file_in = drs_obj["main"]
            index = drs_obj["index"]
            if start is None:
                start = 0
            if end is None:
                end = -1

            urls = _create_slices(CHUNK_SIZE, id, reference_name, start, end, file_type)
        response = {
            'htsget': {
                'format': drs_obj["format"],
                'urls': urls
            }
        }
        return response, 200
    return f"No {file_type} found for id: {id}, try using the other endpoint", 404


# This is specific to our particular use case: a DRS object that represents a
# particular sample can have a variant or read file and an associated index file.
# We need to query DRS to get the bundling object, which should contain links to
# two contents objects. We can instantiate them into temp files and pass those
# file handles back.
def _get_genomic_obj(object_id):
    result = None
    drs_obj = _describe_drs_object(object_id)
    with tempfile.TemporaryDirectory() as tempdir:
        index_file, status_code1 = _get_local_file(drs_obj['index'], tempdir)
        main_file, status_code2 = _get_local_file(drs_obj['main'], tempdir)
        if status_code2 > 200:
            return { "error": main_file['message'], "status_code": status_code2 }
        if drs_obj['type'] == 'read':
            result = AlignmentFile(main_file, index_filename=index_file)
        else:
            result = VariantFile(main_file, index_filename=index_file)
    return { "file": result, "file_format": drs_obj['format'] }


def _get_local_file(drs_file_obj_id, dir):
    (drs_file_obj, status_code) = drs_operations.get_object(drs_file_obj_id)
    # get access_methods for this drs_file_obj
    for method in drs_file_obj["access_methods"]:
        if "access_id" in method and method["access_id"] != "":
            # we need to go to the access endpoint to get the url and file
            (url, status_code) = drs_operations.get_access_url(None, method["access_id"])
            if status_code < 300:
                f_path = os.path.join(dir, drs_file_obj["name"])
                with open(f_path, mode='wb') as f:
                    with requests.get(url["url"], stream=True) as r:
                        with r.raw as content:
                            f.write(content.data)
                return f_path, 200
            else:
                return url, 500
        else:
            # the access_url has all the info we need
            url_pieces = urlparse(method["access_url"]["url"])
            if url_pieces.scheme == "file":
                if url_pieces.netloc == "" or url_pieces.netloc == "localhost":
                    return url_pieces.path, 200
    return None, 500

# describe an htsget DRS object, but don't open it
def _describe_drs_object(object_id):
    (drs_obj, status_code) = drs_operations.get_object(object_id)
    if status_code != 200:
        return None
    result = {
        "name": object_id
    }
    # drs_obj should have two contents objects
    if "contents" in drs_obj:
        for contents in drs_obj["contents"]:
            # get each drs object (should be the genomic file and its index)
            print(contents)
            # if sub_obj.name matches an index file regex, it's an index file
            index_match = re.fullmatch('.+\.(..i)$', contents["name"])

            # if sub_obj.name matches a bam/sam/cram file regex, it's a read file
            read_match = re.fullmatch('.+\.(.+?am)$', contents["name"])

            # if sub_obj.name matches a vcf/bcf file regex, it's a variant file
            variant_match = re.fullmatch('.+\.(.cf)(\.gz)*$', contents["name"])

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
    if 'type' not in result:
        return {"error": f"drs object {object_id} does not represent an htsget object", "status_code": 404}
    return result
