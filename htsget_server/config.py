import configparser

config = configparser.ConfigParser()
config.read('./config.ini')

AUTHZ = config['authz']

DB_PATH = config['paths']['DBPath']
LOCAL_FILE_PATH = config['paths']['LocalFilesPath']

MINIO = config['minio']

CHUNK_SIZE = int(config['DEFAULT']['ChunkSize'])

PORT = config['DEFAULT']['Port']