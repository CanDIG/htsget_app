import sqlite3
from flask import request
from pysam import VariantFile, AlignmentFile
from tempfile import NamedTemporaryFile
from ga4gh.dos.client import Client
import os
from flask import send_file
from minio import Minio
from minio.error import ResponseError
import configparser

config = configparser.ConfigParser()
config.read('./config.ini')

LOCAL_FILES_PATH = config['paths']['LocalFilesPath']
LOCAL_DB_PATH = config['paths']['LocalDBPath']
TEMPORARY_FILES_PATH = config['paths']['TemporaryFilesPath']
CHUNK_SIZE =  int( config['DEFAULT']['ChunkSize'] )
FILE_RETRIEVAL = config['DEFAULT']['FileRetrieval']
DRS_URL = config['paths']['DRSPath']
MINIO_END_POINT = config['minio']['EndPoint']
MINIO_ACCESS_KEY = config['minio']['AccessKey']
MINIO_SECRET_KEY = config['minio']['SecretKey']

def get_reads(id, reference_name = None, start = None, end = None):
    """
    Return URIs of reads:

    :param id: id of the file ( e.g. id=HG02102 for file HG02102.vcf.gz )
    :param reference_name: Chromesome Number
    :param start: Index of file to begin at
    :param end: Index of file to end at
    """
    obj = {}
    if FILE_RETRIEVAL == "db":
        obj = _get_urls_db("read", id, reference_name, start, end)
    elif FILE_RETRIEVAL == "minio":
        obj = _get_urls_drs("read", id, reference_name, start, end)

    response = obj["response"]
    http_status_code = obj["http_status_code"]
    return response, http_status_code

def get_variants(id, reference_name = None, start = None, end = None):
    """ 
    Return URIs of variants:

    :param id: id of the file ( e.g. id=HG02102 for file HG02102.vcf.gz )
    :param reference_name: Chromesome Number
    :param start: Index of file to begin at
    :param end: Index of file to end at
    """
    obj = {}
    if FILE_RETRIEVAL == "db":
        obj = _get_urls_db("variant", id, reference_name, start, end)
    elif FILE_RETRIEVAL == "minio":
        obj = _get_urls_drs("variant", id, reference_name, start, end)
    
    response = obj["response"]
    http_status_code = obj["http_status_code"]
    return response, http_status_code

def get_data(id, reference_name=None, format=None, start=None, end=None):
    # start = 17148269, end = 17157211, reference_name = 21
    """
    Returns the specified variant or read file:

    :param id: id of the file ( e.g. id=HG02102 for file HG02102.vcf.gz )
    :param reference_name: Chromesome Number
    :param start: Index of file to begin at
    :param end: Index of file to end at
    """

    # how to get file name? - make a query to drs based on ID

    file_name = ""
    file_format = ""
    if FILE_RETRIEVAL == "db":
        file = _get_file_by_id(id)
        file_extension = file[0][1]
        file_format = file[0][2]
        file_name = f"{id}{file_extension}"
    elif FILE_RETRIEVAL == "minio":
        file_name = _get_file_name(id)
        file_format = "VCF" #hardcoded for now
        _download_minio_file(file_name)
        
    ntf = NamedTemporaryFile(prefix='htsget', suffix='', dir=TEMPORARY_FILES_PATH, mode='wb', delete=False)

    file_in_path = f"{LOCAL_FILES_PATH}/{file_name}"
    file_in = None
    file_out = None
    if file_format == "VCF" or file_format == "BCF": # Variants
        file_in = VariantFile(file_in_path)
        file_out = VariantFile(ntf.name, 'w', header=file_in.header)
    elif file_format == "BAM" or file_format == "CRAM": # Reads
        reference_name = f"chr{reference_name}"
        file_in = AlignmentFile(file_in_path)
        file_out = AlignmentFile(ntf.name, 'w', header=file_in.header)
    for rec in file_in.fetch(reference_name, start, end):
        file_out.write(rec)
    file_in.close()
    file_out.close()
    
    # return send_file(ntf.name)
    buf_size = 1000000
    with open(ntf.name, 'rb') as f:
        data = f.read(buf_size)
        print(ntf.name)
        os.remove(ntf.name)
        return data, 200
    


""" Helper Functions"""

def _execute(query, param_obj):
    """
    Execute sql query
    """
    conn = sqlite3.connect(LOCAL_DB_PATH)
    c = conn.cursor()
    c.execute(query, param_obj)

    res = c.fetchall()

    conn.commit()
    conn.close()    

    return res

def _get_file_by_id(id):
    query = """SELECT * FROM  files WHERE id = (:id) LIMIT 1"""
    param_obj = {'id': id}
    return _execute(query, param_obj)


def _create_slice(arr, id, reference_name, slice_start, slice_end):
    """
    Creates slice and appends it to array of urls (mutated)
    """
    url = f"http://{request.host}/data?id={id}&reference_name={reference_name}&start={slice_start}&end={slice_end}"
    arr.append({ 'url': url, })

def _create_slices(chunk_size, id, reference_name, start, end):
    """
    Returns array of slices of URLs
    """
    urls = []
    chunks = int( (end - start) / chunk_size )
    slice_start = start
    slice_end = 0
    if chunks >= 1 and start != None and end != None:
        for i in range(chunks):
            slice_end = slice_start + chunk_size
            _create_slice(urls, id, reference_name, slice_start, slice_end)
            slice_start = slice_end
        _create_slice(urls, id, reference_name, slice_start, end)
    else: # One slice only
        url = f"http://{request.host}/data?id={id}"
        if( reference_name is not None ):
            url += f"&reference_name={reference_name}"
        urls.append({ "url": url })

    return urls

def _get_urls_drs(file_type, id, reference_name = None, start = None, end = None):
    """
    Return a list of URLS for Read or Variant from a given ID 
    """

    file_exists = False
    client = Client(DRS_URL)
    c = client.client
    try:
        response = c.GetDataObject(data_object_id = id).result() 
        file_exists = True
        file_format = "VCF" # hardcode for now
    except:
        file_exists = False

    if file_exists:
        urls = _create_slices(CHUNK_SIZE, id, reference_name, start, end)
        response = {
            'htsget': {
                'format': file_format,
                'urls': urls 
                }
            }
        return {"response": response, "http_status_code": 200}
    else:
        err = f"No {file_type} found for id: {id}" 
        return {"response": err, "http_status_code": 404}

def _get_urls_db(file_type, id, reference_name = None, start = None, end = None):
    """
    Return a list of URLS for Read or Variant from a given ID using sqlite database

    :param file_type: "read" or "variant"
    """
    if file_type not in ["variant", "read"]:
        raise ValueError("File type must be 'variant' or 'read'")

    file = _get_file_by_id(id) # returns an array of tuples
    file_exists = len(file) != 0 
    if file_exists:
        file_name = file[0][0] + file[0][1]
        file_format = file[0][2]

        if start is None:
            start = _get_index("start", file_name, file_type)
        if end is None:
            end = _get_index("end", file_name, file_type)

        urls = _create_slices(CHUNK_SIZE, id, reference_name, start, end)
        response = {
            'htsget': {
                'format': file_format,
                'urls': urls 
                }
            }
        return {"response": response, "http_status_code": 200}
    else:
        err = f"No {file_type} found for id: {id}" 
        return {"response": err, "http_status_code": 404}

def _get_index(position, file_name, file_type):
    """
    Get the first or last index of a reads or variant file.
    File must be stored locally

    :param position: Get either first or last index. 
        Options: first - "start"
                 last - "end"
    :param file_name: name of file
    :param file_type: Read or Variant
    """
    position = position.lower()
    if position not in ["start", "end"]:
        return "That position is not available"

    file_type = file_type.lower()
    if file_type not in ["variant", "read"]:
        return "That format is not available"
    
    file_in = 0
    if file_type == "variant":
        file_path = LOCAL_FILES_PATH + f"/{file_name}"
        file_in = VariantFile(file_path, "r")
    elif file_type == "read":
        file_path = LOCAL_FILES_PATH + f"/{file_name}"
        file_in = AlignmentFile(file_path, "r")
    
    # get the required index
    if position == "start":
        start = 0
        for rec in file_in.fetch():
            start = rec.pos
            break
        return start
    elif position == "end":       
        end = 0
        for rec in file_in.fetch():
            end = rec.pos
        return end

def _get_file_name(id):
    """
    Make query to DRS to get all file names associated to ID
    """
    client = Client(DRS_URL)
    c = client.client

    # assume id will be NA18537
    response = c.GetDataObject(data_object_id=id).result()
    return response['data_object']["name"]

def _download_minio_file(file_name):
    """
    Download file from minio

    - When do we delete the downloaded file?
    - assume indexed file is stored in minio and DRS
    """
    minioClient = Minio(MINIO_END_POINT,
                        access_key = MINIO_ACCESS_KEY,
                        secret_key = MINIO_SECRET_KEY,
                        secure = True)

    file_path = f"{LOCAL_FILES_PATH}/{file_name}" # path to download the file
    file_name_indexed = file_name + ".tbi" # hard coded
    file_path_indexed = f"{LOCAL_FILES_PATH}/{file_name_indexed}" # path to download indexed file
    bucket = 'test'

    # Create the file
    try:
        f = open(file_path, "x")
        f.close()

        f = open(file_path_indexed, "x")
        f.close()
    except:
        # File already exists, do nothing
        pass

    # download the required file into file_path
    try:
        minioClient.fget_object(bucket, file_name, file_path)
        minioClient.fget_object(bucket, file_name_indexed, file_path_indexed)
    except ResponseError as err:
        print(err)