import sqlite3
from flask import request
from pysam import VariantFile
from tempfile import NamedTemporaryFile
import os


def get_variants(id, ref = None, start = 17148269, end = 17157211):
    """ 
    Return URIs of variants
    """
    query = """SELECT * FROM  files WHERE file_name = (:id)"""
    param_obj = {'id': id}
    result = execute(query, param_obj)  

    if( len(result) != 0 ):
        partition_amt = 10000000
        urls = create_slices(partition_amt, id, ref, start, end)
        response = {
                'format': 'VCF',
                'urls': urls 
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
    
    buf_size = 1000000
    with open(ntf.name, 'rb') as f:
        data = f.read(buf_size)
        os.remove(ntf.name)
        return data, 200
    


# helpers

def execute(query, param_obj):
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

def create_slices(partition_amt, id, ref, start, end):
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
    else:
        url = f"http://{request.host}/data?id={id}"
        if( ref is not None ):
            url += f"&ref={ref}"
        urls.append(url)

    return urls