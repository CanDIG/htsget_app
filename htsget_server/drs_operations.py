from minio import Minio
import connexion
import database
import configparser
from pathlib import Path

config = configparser.ConfigParser()
config.read(Path('./config.ini'))
MINIO_END_POINT = config['minio']['EndPoint']
MINIO_ACCESS_KEY = config['minio']['AccessKey']
MINIO_SECRET_KEY = config['minio']['SecretKey']
MINIO_BUCKET_NAME = config['minio']['BucketName']
LOCAL_FILE_PATH = config['paths']['LocalFilesPath']

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
    try:
        client = Minio(
            MINIO_END_POINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY
        )
        result = client.stat_object(bucket_name=MINIO_BUCKET_NAME, object_name=access_id)
        url = client.presigned_get_object(bucket_name=MINIO_BUCKET_NAME, object_name=access_id)
    except Exception as e:
        return {"message": str(e)}, 500
    return {"url": url}, 200


def post_object():
    new_object = database.create_drs_object(connexion.request.json)
    if "access_methods" in new_object:
        for method in new_object['access_methods']:
            if 'access_id' in method and method['access_id'] != "":
                # check to see if it's already there; otherwise, upload it
                (url_obj, status_code) = get_access_url(new_object['id'], method['access_id'])
                if status_code != 200:
                    try:
                        client = Minio(
                            MINIO_END_POINT,
                            access_key=MINIO_ACCESS_KEY,
                            secret_key=MINIO_SECRET_KEY
                        )
                        #create the minio bucket/object/etc
                        if 'NoSuchBucket' in url_obj['message']:
                            client.make_bucket(MINIO_BUCKET_NAME, location=method['region'])
                        file = Path(LOCAL_FILE_PATH).joinpath(new_object['id'])
                        with Path.open(file, "rb") as fp:
                            result = client.put_object(MINIO_BUCKET_NAME, new_object['id'], fp, file.stat().st_size)
                    except Exception as e:
                        return {"message": str(e)}, 500
    return new_object, 200


def delete_object(object_id):
    try:
        new_object = database.delete_drs_object(object_id)
        return new_object, 200
    except Exception as e:
        return {"message": str(e)}, 500
