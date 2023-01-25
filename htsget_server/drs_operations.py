from minio import Minio
import connexion
import database
from flask import request, Flask
import os
import re
import authz
import requests
from markupsafe import escape
from urllib.parse import parse_qs


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
    app.logger.warning(f"looking for object {object_id}")
    access_url_parse = re.match(r"(.+?)/access_url/(.+)", escape(object_id))
    if access_url_parse is not None:
        return get_access_url(access_url_parse.group(1), access_url_parse.group(2))
    new_object = database.get_drs_object(escape(object_id), expand)
    if new_object is None:
        return {"message": "No matching object found"}, 404
    return new_object, 200


def list_objects():
    return database.list_drs_objects(), 200


@app.route('/ga4gh/drs/v1/objects/<object_id>/access_url/<path:access_id>')
def get_access_url(object_id, access_id):
    app.logger.warning(f"looking for url {access_id}")
    if object_id is not None:
        auth_code = authz.is_authed(escape(object_id), request)
        if auth_code != 200:
            return {"message": f"Not authorized to access object {object_id}"}, auth_code
    id_parse = re.match(r"((https*:\/\/)*.+?)\/(.+?)\/(.+?)(\?(.+))*$", access_id)
    if id_parse is not None:
        endpoint = id_parse.group(1)
        bucket = id_parse.group(3)
        object_name = id_parse.group(4)
        url = None
        if id_parse.group(5) is None:
            url, status_code = authz.get_s3_url(request, s3_endpoint=endpoint, bucket=bucket, object_id=object_name)
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
            url, status_code = authz.get_s3_url(request, s3_endpoint=endpoint, bucket=bucket, object_id=object_name, access_key=access, secret_key=secret, public=public)
        if status_code == 200:
            return {"url": url}, status_code
        return {"error": url}, 500
    else:
        return {"message": f"Malformed access_id {access_id}: should be in the form endpoint/bucket/item", "method": "get_access_url"}, 400


def post_object():
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    new_object = database.create_drs_object(connexion.request.json)
    return new_object, 200


@app.route('/ga4gh/drs/v1/objects/<path:object_id>')
def delete_object(object_id):
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    try:
        new_object = database.delete_drs_object(escape(object_id))
        return new_object, 200
    except Exception as e:
        return {"message": str(e)}, 500


def list_datasets():
    datasets = database.list_datasets()
    if authz.is_site_admin(request):
        return datasets
    authorized_datasets = authz.get_authorized_datasets(request)
    return list(set(map(lambda x: x['id'], datasets)) & set(authorized_datasets)), 200


def post_dataset():
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    new_dataset = database.create_dataset(connexion.request.json)
    return new_dataset, 200


def get_dataset(dataset_id):
    new_dataset = database.get_dataset(dataset_id)
    if new_dataset is None:
        return {"message": "No matching dataset found"}, 404
    if authz.is_site_admin(request):
        return new_dataset, 200
    authorized_datasets = authz.get_authorized_datasets(request)
    if new_dataset["id"] in authorized_datasets:
        return new_dataset, 200
    return {"message": f"Not authorized to access dataset {dataset_id}"}, 403


def delete_dataset(dataset_id):
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    try:
        new_dataset = database.delete_dataset(dataset_id)
        return new_dataset, 200
    except Exception as e:
        return {"message": str(e)}, 500
