import configparser
import os
from minio import Minio

config = configparser.ConfigParser()
config.read('./config.ini')

AUTHZ = config['authz']

DB_PATH = config['paths']['DBPath']
LOCAL_FILE_PATH = config['paths']['LocalFilesPath']

MINIO = config['minio']
MINIO_END_POINT = MINIO['EndPoint']
MINIO_ACCESS_KEY = MINIO['AccessKey']
MINIO_SECRET_KEY = MINIO['SecretKey']
MINIO_BUCKET_NAME = MINIO['BucketName']

CHUNK_SIZE = int(config['DEFAULT']['ChunkSize'])

PORT = config['DEFAULT']['Port']

TEST_KEY = os.environ.get("HTSGET_TEST_KEY")
if os.environ.get("USE_MINIO_SANDBOX") == "True":
    USE_MINIO_SANDBOX = True

def get_minio_client():
    if USE_MINIO_SANDBOX:
        return Minio(
            "play.min.io:9000",
            access_key="Q3AM3UQ867SPQQA43P2F",
            secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
        ), MINIO_BUCKET_NAME
    return Minio(
        MINIO_END_POINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY
    ), MINIO_BUCKET_NAME
