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

def test_file_without_start_end(id, reference_name):
    # url = f"http://0.0.0.0:5000/data?id={id}&reference_name={reference_name}"

    # res = requests.get(url)
    # # print(res.content.decode()
    # data = res.content.decode()
    # f = open('./NA18537.vcf.gz.tbi', 'wb')
    # f.write(data.encode('utf-8'))
    file_one = VariantFile("./NA18537_2.vcf.gz")
    file_two = VariantFile("../data/files/NA18537.vcf.gz")
    for x, y in zip(file_one.fetch(), file_two.fetch()):
        print(f"X: {x.pos}            Y: {y.pos}")
        break


test_file_without_start_end('NA18537', '21')

