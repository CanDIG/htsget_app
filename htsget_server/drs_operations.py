import connexion
import database
from flask import request, Flask
import os
import os.path
import re
import authz
from markupsafe import escape
from pysam import VariantFile, AlignmentFile
from urllib.parse import parse_qs, urlparse, urlencode
from config import INDEXING_PATH
from time import sleep
from random import randint
from candigv2_logging.logging import log_message


app = Flask(__name__)


# API endpoints
def get_service_info():
    return {
        "id": "org.candig.drs",
        "name": "CanDIG baby DRS service",
        "type": {
            "group": "org.ga4gh",
            "artifact": "drs",
            "version": "v1.2.0"
        },
        "description": "A DRS-compliant server for CanDIG genomic data",
        "organization": {
            "name": "CanDIG",
            "url": "https://www.distributedgenomics.ca"
        },
        "version": "1.0.0"
    }


@app.route('/ga4gh/drs/v1/objects/<path:object_id>')
def get_object(object_id, expand=False):
    log_message("DEBUG",f"looking for object {object_id}")
    access_url_parse = re.match(r"(.+?)/access_url/(.+)", escape(object_id))
    if access_url_parse is not None:
        return get_access_url(access_url_parse.group(1), access_url_parse.group(2))
    new_object = None
    if object_id is not None:
        new_object = database.get_drs_object(escape(object_id), expand)
        auth_code = authz.is_authed(escape(object_id), request)
        if auth_code != 200:
            return {"message": f"Not authorized to access object {object_id}"}, auth_code
    if new_object is None:
        return {"message": "No matching object found"}, 404
    return new_object, 200


def get_object_for_drs_uri(drs_uri):
    drs_uri_parse = re.match(r"drs:\/\/(.+)\/(.+)", drs_uri)
    if drs_uri_parse is None:
        return {"message": f"Incorrect format for DRS URI: {drs_uri}"}, 401
    if drs_uri_parse.group(1) in os.getenv("HTSGET_URL"):
        return get_object(drs_uri_parse.group(2))
    return {"message": f"Couldn't resolve DRS server {drs_uri_parse.group(1)}"}, 401


def list_objects(cohort_id=None):
    return database.list_drs_objects(cohort_id=cohort_id), 200


@app.route('/ga4gh/drs/v1/objects/<object_id>/access_url/<path:access_id>')
def get_access_url(object_id, access_id, request=request):
    if object_id is not None:
        auth_code = authz.is_authed(escape(object_id), request)
        if auth_code != 200:
            return {"message": f"Not authorized to access object {object_id}"}, auth_code
    return _get_access_url(access_id)


def post_object(tries=1):
    cohort_id = connexion.request.json["cohort"]
    object_id = connexion.request.json['id']
    if not authz.is_cohort_authorized(request, cohort_id):
        return {"message": "User is not authorized to POST"}, 403
    if tries > 3:
        raise Exception(f"Exception in post_object {object_id}, too many tries")
    elif tries > 1:
        # if this isn't the first try, pause for a bit and then try again
        sleep(randint(1,10)/2)
    try:
        new_object = database.create_drs_object(connexion.request.json)
    except Exception as e:
        log_message("DEBUG",f"Exception in post_object {object_id}: {str(e)}, trying again")
        return post_object(tries=tries+1)
    return new_object, 200


@app.route('/ga4gh/drs/v1/objects/<path:object_id>')
def delete_object(object_id):
    obj = database.get_drs_object(object_id)
    if obj is not None:
        cohort_id = obj["cohort"]
        if not authz.is_cohort_authorized(request, cohort_id):
            return {"message": "User is not authorized to POST"}, 403
        try:
            new_object = database.delete_drs_object(escape(object_id))
            return new_object, 200
        except Exception as e:
            return {"message": str(e)}, 500
    else:
        return {"message": f"object {object_id} not found"}, 404


def list_cohorts():
    cohorts = database.list_cohorts()
    if cohorts is None:
        return [], 404
    try:
        if authz.is_site_admin(request):
            return list(map(lambda x: x['id'], cohorts)), 200
        authorized_cohorts = authz.get_authorized_cohorts(request)
        return list(set(map(lambda x: x['id'], cohorts)).intersection(set(authorized_cohorts))), 200
    except Exception as e:
        return [], 500


def post_cohort():
    if not authz.is_cohort_authorized(request, connexion.request.json['id']):
        return {"message": "User is not authorized to POST"}, 403
    new_cohort = database.create_cohort(connexion.request.json)
    return new_cohort, 200


def get_cohort(cohort_id):
    new_cohort = database.get_cohort(cohort_id)
    if new_cohort is None:
        return {"message": "No matching cohort found"}, 404
    if authz.is_cohort_authorized(request, cohort_id):
        return new_cohort, 200
    return {"message": f"Not authorized to access cohort {cohort_id}"}, 403


def delete_cohort(cohort_id):
    if not authz.is_cohort_authorized(request, cohort_id):
        return {"message": "User is not authorized to POST"}, 403
    try:
        new_cohort = database.delete_cohort(cohort_id)
        return new_cohort, 200
    except Exception as e:
        return {"message": str(e)}, 500


def get_cohort_status(cohort_id):
    new_cohort = database.get_cohort(cohort_id)
    if new_cohort is None:
        return {"message": "No matching cohort found"}, 404
    if not authz.is_cohort_authorized(request, cohort_id):
        return {"message": f"Not authorized to access cohort {cohort_id}"}, 403

    # get the objects in the cohort:
    result = {
        "index_complete": [],
        "index_in_progress": [],
        "index_errored": []
    }
    for drs_uri in new_cohort['drsobjects']:
        drs_obj, status_code = get_object_for_drs_uri(drs_uri)
        if "indexed" in drs_obj:
            if drs_obj['indexed'] == 1:
                result['index_complete'].append(drs_uri)
            else:
                # look for index touch file, see if there are errors there:
                file_path = os.path.join(INDEXING_PATH, f"{cohort_id}_{drs_obj['id']}")
                err_obj = {
                    "drs_uri": drs_uri,
                    "errors": []
                }
                if os.path.exists(file_path):
                    with open(file_path) as f:
                        err_obj["errors"].extend(f.readlines())
                        if len(err_obj["errors"]) > 0:
                            result['index_errored'].append(err_obj)
                        else:
                            result['index_in_progress'].append(drs_uri)
    return result, 200


# This is specific to our particular use case: a DRS object that represents a
# particular sample can have a variant or read file and an associated index file.
# We need to query DRS to get the bundling object, which should contain links to
# two contents objects.
def _get_genomic_obj(object_id):
    result = {'status_code': 200}
    drs_obj = _describe_drs_object(object_id)
    if drs_obj is None:
        return { "message": f"{object_id} not found", "status_code": 404}
    index_result = _get_file_path(drs_obj['index'])
    if 'message' in index_result:
        result = index_result
    else:
        result['type'] = drs_obj['type']
        main_result = _get_file_path(drs_obj['main'])
        if 'message' in main_result:
            result = main_result
        else:
            if "samples" in drs_obj:
                result['samples'] = drs_obj['samples']
            try:
                result['file_format'] = drs_obj['format']
                if drs_obj['type'] == 'read':
                    result['file'] = AlignmentFile(main_result['path'], index_filename=index_result['path'])
                else:
                    result['file'] = VariantFile(main_result['path'], index_filename=index_result['path'])
            except Exception as e:
                return { "message": str(e), "status_code": 500, "method": f"_get_genomic_obj({object_id})"}
    return result


# describe an htsget DRS object, but don't open it
def _describe_drs_object(object_id):
    drs_obj = database.get_drs_object(object_id)
    if drs_obj is None:
        return None
    result = {
        "name": object_id
    }
    # drs_obj should have a main contents, index contents, and sample contents
    if "contents" in drs_obj:
        for contents in drs_obj["contents"]:
            # get each drs object (should be the genomic file and its index)
            # if sub_obj.name matches an index file regex, it's an index file
            index_match = re.fullmatch(r'.+\.(...*i)$', contents["name"])

            # if sub_obj.name matches a bam/sam/cram file regex, it's a read file
            read_match = re.fullmatch(r'.+\.(.+?am)$', contents["name"])

            # if sub_obj.name matches a vcf/bcf file regex, it's a variant file
            variant_match = re.fullmatch(r'.+\.(.cf)(\.gz)*$', contents["name"])

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
            else:
                if "samples" not in result:
                    result['samples'] = {}
                result['samples'][contents['id']] = contents['name']

    if 'type' not in result:
        return {"message": f"drs object {object_id} does not represent an htsget object", "status_code": 404}
    return result


def _get_file_path(drs_file_obj_id):
    result = { "path": None, "status_code": 200, "method": f"_get_file_path({drs_file_obj_id})" }
    drs_file_obj = database.get_drs_object(drs_file_obj_id)
    if drs_file_obj is None:
        result["message"] = f"Couldn't find file {drs_file_obj_id}"
        result['status_code'] = 404
        return result
    # get access_methods for this drs_file_obj
    url = ""
    for method in drs_file_obj["access_methods"]:
        if "access_id" in method and method["access_id"] != "":
            # we need to go to the access endpoint to get the url and file
            (url_obj, status_code) = _get_access_url(method["access_id"])
            result["status_code"] = status_code
            if status_code < 300:
                result["path"] = url_obj["url"]
                result["checksum"] = {
                    "type": "etag",
                    "checksum": url_obj["metadata"].etag
                }
                result["size"] = url_obj["metadata"].size
                break
        else:
            # the access_url has all the info we need
            url_pieces = urlparse(method["access_url"]["url"])
            if url_pieces.scheme == "file":
                if url_pieces.netloc == "" or url_pieces.netloc == "localhost":
                    result["path"] = os.path.abspath(url_pieces.path)
                    if not os.path.exists(result["path"]):
                        result['message'] = f"No file exists at {result['path']} on the server."
                        result['status_code'] = 404
                    else:
                        if len(drs_file_obj["checksums"]) > 0:
                            result["checksum"] = drs_file_obj["checksums"][0]
                        else:
                            result["checksum"] = None
                        result["size"] = os.path.getsize(result["path"])
    if result['path'] is None:
        message = url_obj
        if "error" in url_obj:
            message = url_obj["error"]
        result['message'] = f"No file was found for drs_obj {drs_file_obj_id}: {message}"
        result['status_code'] = 404
        result.pop('path')
    return result


def _get_access_url(access_id):
    log_message("DEBUG",f"looking for url {access_id}")
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
