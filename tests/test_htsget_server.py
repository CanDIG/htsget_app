import pytest
import requests
import os
from tempfile import NamedTemporaryFile
from pysam import VariantFile, AlignmentFile, TabixFile
from urllib import parse
import configparser
from pathlib import Path


config = configparser.ConfigParser()
config.read(Path('./config.ini'))

BASE_PATH = config['DEFAULT']['BasePath']
PORT = config['DEFAULT']['Port']
HOST = f"http://localhost:{PORT}{BASE_PATH}"
LOCAL_FILES_PATH = "./data/files"


def invalid_start_end_data():
    return [(17123456, 23588), (9203, 42220938)]


@pytest.mark.parametrize('start, end', invalid_start_end_data())
def test_invalid_start_end(start, end):
    """
    Should return a 400 error if end is smaller than start
    """
    url_v = f"{HOST}/variants?id=NA18537&reference_name=21&start={start}&end={end}"
    url_r = f"{HOST}/reads?id=NA18537&reference_name=21&start={start}&end={end}"

    res_v = requests.get(url_v)
    print(res_v)
    res_r = requests.get(url_r)

    if end < start:
        assert res_v.status_code == 400
        assert res_r.status_code == 400
    else:
        assert True


def existent_file_test_data():
    return [('NA18537', 200), ('NA20787', 200), ('HG203245', 404), ('NA185372', 404)]


@pytest.mark.parametrize('id, expected_status', existent_file_test_data())
def test_existent_file(id, expected_status):
    """
    Should fail with expected error if a file does not exist for given ID
    """
    url_v = f"{HOST}/variants?id={id}&reference_name=21&start=10235878&end=45412368"
    url_r = f"{HOST}/reads?id={id}&reference_name=21&start=10235878&end=45412368"

    res_v = requests.get(url_v)
    res_r = requests.get(url_r)
    assert res_v.status_code == expected_status or res_r.status_code == expected_status


def test_file_without_start_end_data():
    return [('NA18537', '21', '.vcf.gz', 'variant'), ('NA20787', '21', '.vcf.gz', 'variant')]


@pytest.mark.parametrize('id, reference_name, file_extension, file_type', test_file_without_start_end_data())
def test_file_without_start_end(id, reference_name, file_extension, file_type):
    url = f"{HOST}/data?id={id}&reference_name={reference_name}"
    res = requests.get(url)

    file_name = f"{id}{file_extension}"
    path = f"./{file_name}"
    f = open(path, 'wb')
    f.write(res.content)

    file_one = None
    file_two = None
    if file_type == "variant":
        file_one = VariantFile(path)
        file_two = VariantFile(f"{LOCAL_FILES_PATH}/{file_name}")
    elif file_type == "read":
        file_one = AlignmentFile(path)
        file_two = AlignmentFile(f"{LOCAL_FILES_PATH}/{file_name}")
    equal = True
    for x, y in zip(file_one.fetch(), file_two.fetch(contig=reference_name)):
        if x != y:
            equal = False
            os.remove(path)
            assert equal
    os.remove(path)
    assert equal


def test_pull_slices_data():
    return [
        ({"id": 'NA18537', "reference_name": "21",
          "start": 92033, "end": 32345678}, ".vcf.gz", "variant")
    ]


@pytest.mark.parametrize('params, file_extension, file_type', test_pull_slices_data())
def test_pull_slices(params, file_extension, file_type):
    url = f"{HOST}/{file_type}s"
    res = requests.get(url, params)
    res = res.json()
    urls = res['htsget']['urls']

    f_index = 0
    f_name = f"{params['id']}{file_extension}"
    equal = True
    for i in range(len(urls)):
        url = urls[i]['url']
        res = requests.get(url)

        f_slice_name = f"{params['id']}_{i}{file_extension}"
        f_slice_path = f"./{f_slice_name}"
        f_slice = open(f_slice_path, 'wb')
        f_slice.write(res.content)

        f_slice = None
        f = None
        if file_type == "variant":
            f_slice = VariantFile(f_slice_path)
            f = VariantFile(f"{LOCAL_FILES_PATH}/{f_name}")
        elif file_type == "read":
            f_slice = AlignmentFile(f_slice_path)
            f = AlignmentFile(f"{LOCAL_FILES_PATH}/{f_name}")

        # get start index for original file
        for rec in f_slice.fetch():
            f_index = rec.pos - 1
            break
        # compare slice and file line by line
        for x, y in zip(f_slice.fetch(), f.fetch(contig=params['reference_name'], start=f_index)):
            if x != y:
                equal = False
                assert equal
        os.remove(f_slice_path)
    assert equal
