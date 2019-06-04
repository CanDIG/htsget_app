import pytest
import requests
import os
from tempfile import NamedTemporaryFile
from pysam import VariantFile, AlignmentFile, TabixFile

def range_test_data():
    return [(17123456, 23588, 500), (9203, 42220938, 200)]

@pytest.mark.parametrize('start, end, expected_status', range_test_data())
def test_range(start, end, expected_status):
    url_v = f"http://0.0.0.0:5000/variants?id=NA18537&reference_name=21&start={start}&end={end}"
    url_r = f"http://0.0.0.0:5000/reads?id=NA18537&reference_name=21&start={start}&end={end}"

    res_v = requests.get(url_v)
    res_r = requests.get(url_r)
    assert res_v.status_code == expected_status
    assert res_r.status_code == expected_status

def existent_file_test_data():
    return [('NA18537', 200), ('NA20787', 200), ('HG203245', 404), ('NA185372', 404)]

@pytest.mark.parametrize('id, expected_status', existent_file_test_data())
def test_existent_file(id, expected_status):
    url_v = f"http://0.0.0.0:5000/variants?id={id}&reference_name=21&start=10235878&end=45412368"
    url_r = f"http://0.0.0.0:5000/reads?id={id}&reference_name=21&start=10235878&end=45412368"

    res_v = requests.get(url_v)
    res_r = requests.get(url_r)
    assert res_v.status_code == expected_status
    assert res_r.status_code == expected_status

def test_file_without_start_end_data():
    return [('NA18537', '.vcf.gz', 'variant'), ('NA20787', '.vcf.gz', 'variant') ]

@pytest.mark.parametrize('id, file_extension, file_type', test_file_without_start_end_data())
def test_file_without_start_end(id, file_extension, file_type):
    url = f"http://0.0.0.0:5000/data?id={id}"
    res = requests.get(url)

    file_name = f"{id}{file_extension}"
    path = f"./{file_name}"
    f = open(path, 'wb')
    f.write(res.content)
    
    file_one = None
    file_two = None
    if file_type == "variant":
        file_one = VariantFile(path)
        file_two = VariantFile(f"../data/files/{file_name}")
    elif file_type == "read":
        file_one = AlignmentFile(path)
        file_two = AlignmentFile(f"../data/files/{file_name}")    
    equal = True
    for x, y in zip(file_one.fetch(), file_two.fetch()):
        if x != y:
            equal = False
            assert equal
    os.remove(path)
    assert equal



