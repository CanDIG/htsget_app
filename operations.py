import sqlite3
from flask import request
from pysam import VariantFile, AlignmentFile
from tempfile import NamedTemporaryFile
import os
from flask import send_file


def get_variants(id, ref = None, start = None, end = None):
    """ 
    Return URIs of variants
    """
    query = """SELECT * FROM  files WHERE file_name = (:id) LIMIT 1"""
    param_obj = {'id': id}
    result = _execute(query, param_obj)
    file_name = result[0][0] + result[0][1]

    if( len(result) != 0 ):
        if start is None:
            start = _get_start(file_name, "variant")
            print(start)
        if end is None:
            end = _get_end(file_name, "variant")
            print(end)

        partition_amt = 10000000
        urls = _create_slices(partition_amt, id, ref, start, end)
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

def get_data(id, ref=None, format=None, start=None, end=None):
    # start = 17148269, end = 17157211, ref = 21

    ntf = NamedTemporaryFile(prefix='htsget', suffix='', dir='./data/write_files', mode='wb', delete=False)

    vcf_in_path = './data/files/' + id + '.vcf.gz'
    vcf_in = VariantFile(vcf_in_path)
    vcf_out = VariantFile(ntf.name, 'w', header=vcf_in.header)
    for rec in vcf_in.fetch(ref, start, end):
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
    db_path = './data/files.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(query, param_obj)

    res = c.fetchall()

    conn.commit()
    conn.close()    

    return res

def _create_slice(arr, id, ref, slice_start, slice_end):
    """
    Creates slice and appends it to array of urls (mutated)
    """
    url = f"http://{request.host}/data?id={id}&ref={ref}&start={slice_start}&end={slice_end}"
    arr.append({ 'url': url, })

def _create_slices(partition_amt, id, ref, start, end):
    """
    Returns array of slices of URLs
    """
    urls = []
    partitions = int( (end - start) / partition_amt )
    slice_start = start
    slice_end = 0
    if( partitions >= 1 and start != None and end != None ):
        for i in range(partitions):
            slice_end = slice_start + partition_amt
            _create_slice(urls, id, ref, slice_start, slice_end)
            slice_start = slice_end
        _create_slice(urls, id, ref, slice_start, end)
    else: # One slice
        url = f"http://{request.host}/data?id={id}"
        if( ref is not None ):
            url += f"&ref={ref}"
        urls.append({ "url": url})

    return urls

def _get_end(file_name, file_type):
    """
    Get the last index of a reads or variant file

    :param id: name of file
    :param file_type: Read or Variant
    """
    file_type = file_type.lower()
    if file_type not in ["variant", "read"]:
        return "That format is not available"
    
    file_in = 0
    if (file_type == "variant"):
        file_in = VariantFile(f"./data/files/{file_name}", "r")
    elif (file_type == "read"):
        file_in = AlignmentFile(f"./data/files/{file_name}", "r")
    
    # get the last index of file
    end = 0
    for rec in file_in.fetch():
        end = rec.pos

    return end

def _get_start(file_name, file_type):
    """
    Get the first index of a reads or variant file

    :param id: name of file
    :param file_type: Read or Variant
    """
    file_type = file_type.lower()
    if file_type not in ["variant", "read"]:
        return "That format is not available"
    
    file_in = 0
    if (file_type == "variant"):
        file_in = VariantFile(f"./data/files/{file_name}", "r")
    elif (file_type == "read"):
        file_in = AlignmentFile(f"./data/files/{file_name}", "r")
    
    # get the last index of file
    start = 0
    for rec in file_in.fetch():
        start = rec.pos
        break

    return start