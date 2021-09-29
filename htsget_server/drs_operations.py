import os
from flask import send_file, jsonify
from pysam import VariantFile, AlignmentFile
from minio import Minio
from minio.error import InvalidResponseError
import connexion
import database

config = configparser.ConfigParser()
config.read(Path('./config.ini'))
DB_PATH = config['paths']['DBPath']
MINIO_END_POINT = config['minio']['EndPoint']
MINIO_ACCESS_KEY = config['minio']['AccessKey']
MINIO_SECRET_KEY = config['minio']['SecretKey']

# API endpoints
def get_object(object_id, expand=False):
    new_object = database.get_drs_object(object_id, expand)
    if new_object is None:
        return {"message": "No matching object found"}, 404
    return new_object, 200
    
def get_access_url(object_id, access_id):
    try:
        client = Minio(
            MINIO_END_POINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY
        )
        url = client.presigned_get_object(bucket_name="testdaisieh", object_name=access_id)
    except Exception as e:
        return {"message": str(e)}, 500
    return {"url": url}, 200
    
def post_object():
    new_object = database.create_drs_object(connexion.request.json)
    return new_object, 200

