import configparser
import os
from minio import Minio

config = configparser.ConfigParser(interpolation=None)
config.read('./config.ini')

AUTHZ = config['authz']
CANDIG_OPA_SITE_ADMIN_KEY = os.getenv("CANDIG_OPA_SITE_ADMIN_KEY", "site_admin")
HTSGET_URL = os.getenv("HTSGET_URL", f"http://localhost:{config['DEFAULT']['Port']}")

DB_PATH = config['paths']['DBPath']
if os.environ.get("DB_PATH") is not None:
    DB_PATH = f"sqlite:///{os.environ.get('DB_PATH')}"
LOCAL_FILE_PATH = config['paths']['LocalFilesPath']

CHUNK_SIZE = int(config['DEFAULT']['ChunkSize'])

BUCKET_SIZE = int(config['DEFAULT']['BucketSize'])

PORT = config['DEFAULT']['Port']

TEST_KEY = os.getenv("HTSGET_TEST_KEY", "testtesttest")

USE_MINIO_SANDBOX = False
if os.environ.get("USE_MINIO_SANDBOX") == "True":
    USE_MINIO_SANDBOX = True

VAULT_S3_TOKEN = os.getenv("VAULT_S3_TOKEN", "none")

DEBUG_MODE = False
if os.getenv("DEBUG_MODE", "1") == "1":
    DEBUG_MODE = True
