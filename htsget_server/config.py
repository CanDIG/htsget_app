import configparser
import os
import re
from minio import Minio

config = configparser.ConfigParser(interpolation=None)
config.read(os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}/../config.ini"))

AUTHZ = config['authz']
HTSGET_URL = os.getenv("HTSGET_URL", f"http://localhost:{config['DEFAULT']['Port']}")

if os.environ.get("PGPASSWORD") is not None:
    password = os.environ.get("PGPASSWORD")
elif os.environ.get("POSTGRES_PASSWORD_FILE") is not None and os.path.exists(os.environ.get("POSTGRES_PASSWORD_FILE")):
    with open(os.environ.get("POSTGRES_PASSWORD_FILE"), 'r') as file:
        password = file.read()
else:
    raise Exception("Could not determine how to get PostGres password")

DB_PATH = re.sub("PASSWORD", password, config['paths']['PGPath'])
DB_PATH = re.sub("HOST", os.environ.get("DB_PATH"), DB_PATH)
print(f"Password is: {password}")

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
