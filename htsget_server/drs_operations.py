from minio import Minio
import connexion
import database
from pathlib import Path
from config import LOCAL_FILE_PATH, get_minio_client
from flask import request
import os

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
    client, bucket = get_minio_client()
    try:
        result = client.stat_object(bucket_name=bucket, object_name=access_id)
        url = client.presigned_get_object(bucket_name=bucket, object_name=access_id)
    except Exception as e:
        return {"message": str(e)}, 500
    return {"url": url}, 200


def post_object():
    client, bucket = get_minio_client()
    new_object = database.create_drs_object(connexion.request.json)
    if "access_methods" in new_object:
        for method in new_object['access_methods']:
            if 'access_id' in method and method['access_id'] != "":
                # check to see if it's already there; otherwise, upload it
                (url_obj, status_code) = get_access_url(new_object['id'], method['access_id'])
                if status_code != 200:
                    try:
                        #create the minio bucket/object/etc
                        if 'NoSuchBucket' in url_obj['message']:
                            if 'region' in method:
                                client.make_bucket(bucket, location=method['region'])
                            else:
                                client.make_bucket(bucket)
                        file = Path(LOCAL_FILE_PATH).joinpath(new_object['id'])
                        with Path.open(file, "rb") as fp:
                            result = client.put_object(bucket, new_object['id'], fp, file.stat().st_size)
                    except Exception as e:
                        return {"message": str(e)}, 500
    return new_object, 200


def delete_object(object_id):
    try:
        new_object = database.delete_drs_object(object_id)
        return new_object, 200
    except Exception as e:
        return {"message": str(e)}, 500


def list_datasets():
    datasets = database.list_datasets()
    return datasets, 200
    

def post_dataset():
    new_dataset = database.create_dataset(connexion.request.json)
    return new_dataset, 200
    
    
def get_dataset(dataset_id):
    new_dataset = database.get_dataset(dataset_id)
    if new_dataset is None:
        return {"message": "No matching dataset found"}, 404
    return new_dataset, 200


def delete_dataset(dataset_id):
    try:
        new_dataset = database.delete_dataset(dataset_id)
        return new_dataset, 200
    except Exception as e:
        return {"message": str(e)}, 500
