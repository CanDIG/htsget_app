import os
import re
import tempfile
import requests
from flask import request, send_file, Flask
from pysam import VariantFile, AlignmentFile
from urllib.parse import urlparse
import drs_operations
import database
import authz
import json
from config import CHUNK_SIZE, HTSGET_URL
from markupsafe import escape


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
def index_variants(id_=None):
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to index variants"}, 403
    if id_ is not None:
        # look for existing variantfile
        varfile = database.get_variant_file(_id)
        if varfile is not None:
            return varfile, 200
        # if none, look for a genomic drs object and create a variantfile from that
        gen_obj = _get_genomic_obj(request, id_)
        if gen_obj is None:
            return {"message": f"No variant with id {id_} exists"}, 404
        varfile = database.create_variantfile({"id": gen_obj["id"]})
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


def _create_slice(arr, id, reference_name, slice_start, slice_end, file_type):
    """
    Creates slice and appends it to array of urls

    :param arr: The array to store urls
    :param id: ID of the file
    :param reference_name: The Chromosome number
    :param slice_start: Starting index of a slice
    :param slice_end: Ending index of a slice
    """
    url = f"{HTSGET_URL}/htsget/v1/{file_type}s/data/{id}?referenceName={reference_name}&start={slice_start}&end={slice_end}"
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
    chunks = int((end - start)/chunk_size)
    slice_start = start
    slice_end = 0
    if chunks >= 1 and start is not None and end is not None:
        for i in range(chunks):
            slice_end = slice_start + chunk_size
            _create_slice(urls, id, reference_name, slice_start, slice_end, file_type)
            slice_start = slice_end
        _create_slice(urls, id, reference_name, slice_start, end, file_type)
    else:  # One slice only
        url = f"{HTSGET_URL}/htsget/v1/{file_type}s/data/{id}"
        if reference_name and start and end:
            url += f"?referenceName={reference_name}&start={start}&end={end}"
        urls.append({"url": url})

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
    if end is not None and end < start:
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
    gen_obj = _get_genomic_obj(request, id_)
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
            try:
                fetch = file_in.fetch(contig=reference_name, start=start, end=end)
            except ValueError as e:
                return {"error": str(e)}, 400

            for rec in fetch:
                file_out.write(rec)

        file_in.close()
        file_out.close()

        # Send the temporary file as the response
        response = send_file(path_or_file=ntf.name,
                             attachment_filename=file_name, as_attachment=True)
        response.headers["x-filename"] = file_name
        response.headers["Access-Control-Expose-Headers"] = 'x-filename'
        os.remove(ntf.name)
        return response, 200
    return { "message": "no object matching id found" }, 404
  
  
def _get_urls(file_type, id, reference_name=None, start=None, end=None, _class=None):
    """
    Searches for file from ID and Return URLS for Read/Variant

    :param file_type: "read" or "variant"
    :param id: ID of a file
    :param reference_name: Chromosome Number
    :param start: Desired starting index of the file
    :param end: Desired ending index of the file
    """
    if end is not None and end < start:
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

    gen_obj = _get_genomic_obj(request, id)
    if gen_obj is not None:
        if "error" in gen_obj:
            return gen_obj['error'], gen_obj['status_code']
        if _class == "header":
            urls = [{"url": f"{HTSGET_URL}/htsget/v1/{file_type}s/data/{id}?class=header",
            "class": "header"}]
        else:
                file_in = gen_obj["file"]
                if start is None:
                    start = _get_index("start", file_in)
                if end is None:
                    end = _get_index("end", file_in)

                urls = _create_slices(CHUNK_SIZE, id, reference_name, start, end, file_type)
        response = {
            'htsget': {
                'format': gen_obj["file_format"],
                'urls': urls
            }
        }
        return response, 200
    return f"No {file_type} found for id: {id}, try using the other endpoint", 404


def _get_index(position, file_in):
    """
    Get the first or last index of a reads or variant file.

    :param position: Get either first or last index.
        Options: first - "start"
                 last - "end"
    :param id: ID of a file
    """
    position = position.lower()
    if position not in ["start", "end"]:
        return "That position is not available"

    # get the required index
    if position == "start":
        start = 0
        for rec in file_in.fetch():
            start = rec.pos
            break
        return start
    elif position == "end":
        end = 0
        for rec in file_in.fetch():
            end = rec.pos
        return end


# This is specific to our particular use case: a DRS object that represents a 
# particular sample can have a variant or read file and an associated index file.
# We need to query DRS to get the bundling object, which should contain links to
# two contents objects. We can instantiate them into temp files and pass those 
# file handles back.
def _get_genomic_obj(request, object_id):
    index_file = None
    variant_file = None
    read_file = None
    file_format = None
    result = None

    with tempfile.TemporaryDirectory() as tempdir:
        (drs_obj, status_code) = drs_operations.get_object(object_id)
        if status_code != 200:
            return None

        # drs_obj should have two contents objects
        for contents in drs_obj["contents"]:
            # get each drs object (should be the genomic file and its index)
            print(contents)
            (sub_obj, status_code) = drs_operations.get_object(contents["name"])

            # if sub_obj.name matches an index file regex, it's an index file
            index_match = re.fullmatch('.+\.(..i)$', sub_obj["name"])

            # if sub_obj.name matches a bam/sam/cram file regex, it's a read file
            read_match = re.fullmatch('.+\.(.+?am)$', sub_obj["name"])

            # if sub_obj.name matches a vcf/bcf file regex, it's a variant file
            variant_match = re.fullmatch('.+\.(.cf)(\.gz)*$', sub_obj["name"])

            if read_match is not None:
                file_format = read_match.group(1).upper()
            elif variant_match is not None:
                file_format = variant_match.group(1).upper()

            # get access_methods for this sub_obj
            for method in sub_obj["access_methods"]:
                if "access_id" in method and method["access_id"] != "":
                    # we need to go to the access endpoint to get the url and file
                    (url, status_code) = drs_operations.get_access_url(None, method["access_id"])
                    if status_code < 300:
                        f_path = os.path.join(tempdir, sub_obj["name"])
                        with open(f_path, mode='wb') as f:
                            with requests.get(url["url"], stream=True) as r:
                                with r.raw as content:
                                    f.write(content.data)
                        if index_match is not None:
                            index_file = f_path
                        elif read_match is not None:
                            read_file = f_path
                        elif variant_match is not None:
                            variant_file = f_path
                    else:
                        return {"error": url, "status_code": status_code}
                else:
                    # the access_url has all the info we need
                    url_pieces = urlparse(method["access_url"]["url"])
                    if url_pieces.scheme == "file":
                        if url_pieces.netloc == "" or url_pieces.netloc == "localhost":
                            if index_match is not None:
                                index_file = url_pieces.path
                            elif read_match is not None:
                                read_file = url_pieces.path
                            elif variant_match is not None:
                                variant_file = url_pieces.path
        if variant_file is not None:
            result = VariantFile(variant_file, index_filename=index_file)
        elif read_file is not None:
            result = AlignmentFile(read_file, index_filename=index_file)

    return { "file": result, "file_format": file_format }
