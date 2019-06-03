import sqlite3
from flask import request
from pysam import VariantFile, AlignmentFile
from tempfile import NamedTemporaryFile
from ga4gh.dos.client import Client
import os
from flask import send_file
from minio import Minio
from minio.error import (ResponseError, BucketAlreadyOwnedByYou,BucketAlreadyExists)
import config

LOCAL_FILES_PATH = config.local_files_path
LOCAL_DB_PATH = config.local_db_path
WRITE_FILES_PATH = config.write_files_path
CHUNK_SIZE =  config.chunk_size
FILE_RETRIEVAL = config.file_retrieval

def get_reads(id, reference_name = None, start = None, end = None):
    """
    Return URIs of reads
    """
    obj = {}
    if FILE_RETRIEVAL == "db":
        obj = _get_urls_db("read", id, reference_name, start, end)
    elif FILE_RETRIEVAL == "drs":
        obj = _get_urls_drs("read", id, reference_name, start, end)

    response = obj["response"]
    http_status_code = obj["http_status_code"]
    return response, http_status_code

def get_variants(id, reference_name = None, start = None, end = None):
    """ 
    Return URIs of variants
    """
    obj = {}
    if FILE_RETRIEVAL == "db":
        obj = _get_urls_db("variant", id, reference_name, start, end)
    elif FILE_RETRIEVAL == "drs":
        obj = _get_urls_drs("variant", id, reference_name, start, end)
    
    response = obj["response"]
    http_status_code = obj["http_status_code"]
    return response, http_status_code

def get_data(id, reference_name=None, format=None, start=None, end=None):
    # start = 17148269, end = 17157211, reference_name = 21
    """
    Returns the specified variant or read file

    notes: perhaps file_type should be added into the URL to avoid querying the file twice
    """

    # how to get file name? - make a query to drs based on ID

    file_type = ""
    file_format = ""
    if FILE_RETRIEVAL == "sql":
        file = _get_file_by_id(id)
        file_type = file[0][1]
        file_format = file[0][2]
    elif FILE_RETRIEVAL == "drs":
        print("getting DRS data")

    ntf = NamedTemporaryFile(prefix='htsget', suffix='', dir=WRITE_FILES_PATH, mode='wb', delete=False)

    file_in_path = f"{LOCAL_FILES_PATH}/{id}{file_type}"
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
    if( chunks >= 1 and start != None and end != None ):
        for i in range(chunks):
            slice_end = slice_start + chunk_size
            _create_slice(urls, id, reference_name, slice_start, slice_end)
            slice_start = slice_end
        _create_slice(urls, id, reference_name, slice_start, end)
    else: # One slice
        url = f"http://{request.host}/data?id={id}"
        if( reference_name is not None ):
            url += f"&reference_name={reference_name}"
        urls.append({ "url": url })

    return urls

def _get_urls(file_type, id, reference_name = None, start = None, end = None):
    """
    Get urls for reads or variants

    :param file_type: "read" or "variant"
    """
    if file_type not in ["variant", "read"]:
        raise ValueError("File type must be 'variant' or 'read'")

    file_exists = False
    file_format = ""
    if  FILE_RETRIEVAL == "sql":
        print("sql")
        file = _get_file_by_id(id) # returns an array of tuples
        file_exists = len(file) != 0 
        if file_exists:
            file_name = file[0][0] + file[0][1]
            file_format = file[0][2]
    elif FILE_RETRIEVAL == "drs":
        print("drs retrieval")
        client = Client("http://0.0.0.0:8080/ga4gh/dos/v1/")
        c = client.client
        try:
            response = c.GetDataObject(data_object_id='na12878_2').result()
            file_exists = True
            file_format = "VCF" # hardcode for now
        except:
            file_exists = False
            print("file not found")
    
    if file_exists:
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

def _get_urls_drs(file_type, id, reference_name = None, start = None, end = None):
    file_exists = False
    client = Client("http://0.0.0.0:8080/ga4gh/dos/v1/")
    c = client.client
    try:
        response = c.GetDataObject(data_object_id='na12878_2').result() #hardcoded for testing
        file_exists = True
        file_format = "VCF" # hardcode for now
    except:
        file_exists = False
        print("file not found") 

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
    Get urls for reads or variants

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
    client = Client("http://0.0.0.0:8080/ga4gh/dos/v1/")
    c = client.client
    models = client.models

    response = c.GetDataObject(data_object_id='na12878_2').result()
    

def _download_minio_file(file_name):
    """
    Download required file from minio

    - When do we delete the downloaded file?
    """
    minioClient = Minio('play.min.io:9000',
                    access_key='Q3AM3UQ867SPQQA43P2F',
                    secret_key='zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG',
                    secure=True)

    file_path = f"{LOCAL_FILES_PATH}/test.vcf.gz" # path to download the file
    bucket = 'test'

    # Create the file
    try:
        f = open(file_path, "x")
        f.close()
    except:
        print("File already exists")

    # download the required file into file_path
    try:
        minioClient.fget_object(bucket, file_name, file_path)
    except ResponseError as err:
        print(err)