from minio import Minio
import connexion
import database
from pathlib import Path
from config import AUTHZ, VAULT_S3_TOKEN, LOCAL_FILE_PATH
from flask import request
import os
import re
import authz
import requests

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


def get_object(object_id, expand=False):
    new_object = database.get_drs_object(object_id, expand)
    if new_object is None:
        return {"message": "No matching object found"}, 404
    return new_object, 200


def list_objects():
    return database.list_drs_objects(), 200


def get_access_url(object_id, access_id):
    if access_id is None:
        return Minio(
            "play.min.io:9000",
            access_key="Q3AM3UQ867SPQQA43P2F",
            secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
        ), "testhtsget"
    id_parse = re.match(r"(https*:\/\/)*(.+?)\/(.+?)\/(.+)$", access_id)
    
    if id_parse is not None:
        response = requests.get(
            AUTHZ['CANDIG_VAULT_URL'] + f"/v1/aws/{id_parse.group(2)}/{id_parse.group(3)}",
            headers={"Authorization": f"Bearer {VAULT_S3_TOKEN}"}
        )
        if response.status_code == 200:
            client = Minio(
                id_parse.group(2),
                access_key=response.json()["data"]["access"],
                secret_key=response.json()["data"]["secret"]
            )
            bucket = id_parse.group(3)
            try:
                result = client.stat_object(bucket_name=bucket, object_name=id_parse.group(4))
                url = client.presigned_get_object(bucket_name=bucket, object_name=id_parse.group(4))
            except Exception as e:
                return {"message": str(e)}, 500
            return {"url": url}, 200
        else:
            return {"message": f"Vault error: {response.text}"}, response.status_code
    else:
        return {"message": f"Malformed access_id {access_id}: should be in the form endpoint/bucket/item"}, 400


def post_object():
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    new_object = database.create_drs_object(connexion.request.json)
    return new_object, 200


def delete_object(object_id):
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    try:
        new_object = database.delete_drs_object(object_id)
        return new_object, 200
    except Exception as e:
        return {"message": str(e)}, 500


def list_datasets():
    datasets = database.list_datasets()
    return datasets, 200
    

def post_dataset():
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    new_dataset = database.create_dataset(connexion.request.json)
    return new_dataset, 200
    
    
def get_dataset(dataset_id):
    new_dataset = database.get_dataset(dataset_id)
    if new_dataset is None:
        return {"message": "No matching dataset found"}, 404
    return new_dataset, 200


def delete_dataset(dataset_id):
    if not authz.is_site_admin(request):
        return {"message": "User is not authorized to POST"}, 403
    try:
        new_dataset = database.delete_dataset(dataset_id)
        return new_dataset, 200
    except Exception as e:
        return {"message": str(e)}, 500
