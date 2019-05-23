import sqlite3
from flask import request
from pysam import VariantFile, AlignmentFile
from tempfile import NamedTemporaryFile
import os
from flask import send_file
import config

LOCAL_FILES_PATH = config.local_files_path
LOCAL_DB_PATH = config.local_db_path
WRITE_FILES_PATH = config.write_files_path
CHUNK_SIZE =  config.chunk_size

def get_variants(id, reference_name = None, start = None, end = None):
    """ 
    Return URIs of variants
    """

    result = _get_file_by_id(id)
    file_name = result[0][0] + result[0][1]

    if( len(result) != 0 ):
        if start is None:
            start = _get_index("start", file_name, "variant")
        if end is None:
            end = _get_index("end", file_name, "variant")

        urls = _create_slices(CHUNK_SIZE, id, reference_name, start, end)
        response = {
            'htsget': {
                'format': 'VCF',
                'urls': urls 
                }
            }
        return response, 200
    else:
        err = "No Variant found for id:" + id
        return err, 404

def get_data(id, reference_name=None, format=None, start=None, end=None):
    # start = 17148269, end = 17157211, reference_name = 21
    """
    Returns the specified variant or read file

    <- Only works for variants for now ->
    """

    ntf = NamedTemporaryFile(prefix='htsget', suffix='', dir=WRITE_FILES_PATH, mode='wb', delete=False)

    vcf_in_path = './data/files/' + id + '.vcf.gz'
    vcf_in = VariantFile(vcf_in_path)
    vcf_out = VariantFile(ntf.name, 'w', header=vcf_in.header)
    for rec in vcf_in.fetch(reference_name, start, end):
        vcf_out.write(rec)
    vcf_in.close()
    vcf_out.close()
    
    # return send_file(ntf.name)
    buf_size = 1000000
    with open(ntf.name, 'rb') as f:
        data = f.read(buf_size)
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

def _get_index(position, file_name, file_type):
    """
    Get the first or last index of a reads or variant file

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
    if (file_type == "variant"):
        file_path = LOCAL_FILES_PATH + f"/{file_name}"
        file_in = VariantFile(file_path, "r")
    elif (file_type == "read"):
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