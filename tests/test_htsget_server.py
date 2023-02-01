import os
import sys
import pytest
import requests
from pysam import AlignmentFile, VariantFile
from pathlib import Path
from authx.auth import get_minio_client, get_access_token, store_aws_credential

# assumes that we are running pytest from the repo directory
sys.path.insert(0,os.path.abspath("htsget_server"))
from config import PORT, LOCAL_FILE_PATH

HOST = os.getenv("TESTENV_URL", f"http://localhost:{PORT}")
TEST_KEY = os.environ.get("HTSGET_TEST_KEY")
USERNAME = os.getenv("CANDIG_SITE_ADMIN_USER")
PASSWORD = os.getenv("CANDIG_SITE_ADMIN_PASSWORD")
MINIO_URL = os.getenv("MINIO_URL")
VAULT_URL = os.getenv("VAULT_URL")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
CWD = os.getcwd()

def get_headers():
    headers={"Test_Key": TEST_KEY}
    try:
        token = get_access_token(username=USERNAME, password=PASSWORD)
        headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        headers["Authorization"] = "Bearer testtest"
    return headers


def test_remove_objects(drs_objects):
    headers = get_headers()
    for obj in drs_objects:
        url = f"{HOST}/ga4gh/drs/v1/objects/{obj['id']}"
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            response = requests.request("DELETE", url, headers=headers)
            print(f"DELETE {obj['name']}: {response.text}")
            assert response.status_code == 200


def test_post_objects(drs_objects):
    """
    Install test objects. Will fail if any post request returns an error.
    """
    # clean up old objects in db:
    url = f"{HOST}/ga4gh/drs/v1/objects"
    headers = get_headers()
    response = requests.request("GET", url, headers=headers)

    client = None

    try:
        bucket = 'testhtsget'
        if MINIO_URL and MINIO_ACCESS_KEY and MINIO_SECRET_KEY:
            if VAULT_URL:
                token = get_access_token(username=USERNAME, password=PASSWORD)
                credential, status_code = store_aws_credential(token=token, endpoint=MINIO_URL, bucket=bucket, access=MINIO_ACCESS_KEY, secret=MINIO_SECRET_KEY, vault_url=VAULT_URL)
                if status_code == 200:
                    client = get_minio_client(token=token, s3_endpoint=credential["endpoint"], bucket=bucket)
            else:
                client = get_minio_client(token=None, s3_endpoint=MINIO_URL, bucket=bucket, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY)
        if client is None:
            client = get_minio_client(bucket=bucket)
    except Exception as e:
        print(str(e))
        assert False
        return {"message": str(e)}, 500

    for obj in drs_objects:
        url = f"{HOST}/ga4gh/drs/v1/objects/{obj['id']}"
        if "contents" not in obj:
            # create access_methods:
            access_id = f"{client['endpoint']}/{client['bucket']}/{obj['id']}"
            if VAULT_URL is None and MINIO_ACCESS_KEY and MINIO_SECRET_KEY:
                access_id += f"?access={MINIO_ACCESS_KEY}&secret={MINIO_SECRET_KEY}"
            obj["access_methods"] = [
                {
                    "type": "s3",
                    "access_id": access_id
                }
            ]
            try:
                file = Path(LOCAL_FILE_PATH).joinpath(obj['id'])
                with Path.open(file, "rb") as fp:
                    result = client['client'].put_object(client['bucket'], obj['id'], fp, file.stat().st_size)
            except Exception as e:
                print(str(e))
                assert False
                return {"message": str(e)}, 500
        url = f"{HOST}/ga4gh/drs/v1/objects"
        response = requests.request("POST", url, json=obj, headers=headers)
        print(f"POST {obj['name']}: {response.text}")
        assert response.status_code == 200


def test_post_update():
    """
    Update NA18537 to local file
    """
    id = "NA18537.vcf.gz"
    url = f"{HOST}/ga4gh/drs/v1/objects/{id}"
    response = requests.request("GET", url, headers=get_headers())
    if response.status_code == 200:
        assert response.status_code == 200
    obj = response.json()

    url = f"{HOST}/ga4gh/drs/v1/objects"
    access_url = f"file:///{LOCAL_FILE_PATH}/NA18537.vcf.gz"
    obj["access_methods"] = [
        {
            "type": "file",
            "access_url": {
                "url": access_url
            }
        }
    ]
    response = requests.post(url, json=obj, headers=get_headers())
    print(response.text)
    assert len(response.json()["access_methods"]) == 1
    assert response.json()["access_methods"][0]["access_url"]["url"] == access_url


def index_variants():
    return [('sample.compressed', None), ('NA18537', None), ('multisample_1', 'HG00096'), ('multisample_2', 'HG00097')]


@pytest.mark.parametrize('sample, genomic_id', index_variants())
def test_index_variantfile(sample, genomic_id):
    url = f"{HOST}/htsget/v1/variants/{sample}/index"
    params = {"genome": "hg37"}
    if genomic_id is not None:
        params["genomic_id"] = genomic_id
    #params['force'] = True
    response = requests.get(url, params=params, headers=get_headers())
    print(response.text)
    assert response.json()["id"] == sample
    if genomic_id is not None:
        assert response.json()["genomic_id"] == genomic_id


def invalid_start_end_data():
    return [(17123456, 23588), (9203, 42220938)]


@pytest.mark.parametrize('start, end', invalid_start_end_data())
def test_invalid_start_end(start, end):
    """
    Should return a 400 error if end is smaller than start
    """
    url_v = f"{HOST}/htsget/v1/variants/NA18537?referenceName=21&start={start}&end={end}"
    url_r = f"{HOST}/htsget/v1/reads/NA18537?referenceName=21&start={start}&end={end}"

    res_v = requests.request("GET", url_v, headers=get_headers())
    res_r = requests.request("GET", url_r, headers=get_headers())

    if end < start:
        assert res_v.status_code == 400
        assert res_r.status_code == 400
    else:
        assert True


def existent_file_test_data():
    return [
        ('NA18537', 'variants',
           {'referenceName': 21, 'start': 10235878, 'end': 45412368},
           200),
        ('NA18537', 'variants',
           {'referenceName': 21},
           200),
        ('NA18537', 'variants',
           {'start': 10235878, 'end': 45412368},
           200),
        ('NA18537', 'variants', {}, 200),
        ('NA20787', 'variants', {}, 200),
        ('NA20787', 'variants',
           {'referenceName': 21},
           200),
        ('HG203245', 'variants', {}, 404)
    ]


@pytest.mark.parametrize('id, type, params, expected_status', existent_file_test_data())
def test_existent_file(id, type, params, expected_status):
    """
    Should fail with expected error if a file does not exist for given ID
    """
    url = f"{HOST}/htsget/v1/{type}/{id}"

    res = requests.request("GET", url, params=params, headers=get_headers())
    assert res.status_code == expected_status
    if res.status_code == 200:
        if 'referenceName' in params:
            assert 'referenceName' in res.json()['htsget']['urls'][1]['url']
            if 'start' in params:
                assert str(params['start']) in res.json()['htsget']['urls'][1]['url']
            if 'end' in params:
                assert str(params['end']) in res.json()['htsget']['urls'][-1]['url']
        else: # if there's no referenceName, there shouldn't be any start or end
            assert 'start' not in res.json()['htsget']['urls'][1]['url']


def pull_slices_data():
    return [
        ({"referenceName": "20",
          "start": 0, "end": 1260000}, 'sample.compressed', ".vcf.gz", "variant"),
        ({}, 'sample.compressed', ".vcf.gz", "variant"),
        ({"referenceName": "21",
          "start": 9410000, "end": 9420000}, 'NA18537', ".vcf.gz", "variant")
    ]


@pytest.mark.parametrize('params, id_, file_extension, file_type', pull_slices_data())
def test_pull_slices(params, id_, file_extension, file_type):
    url = f"{HOST}/htsget/v1/{file_type}s/{id_}"
    res = requests.request("GET", url, params=params, headers=get_headers())
    res = res.json()
    urls = res['htsget']['urls']

    f_index = 0
    f_name = f"{id_}{file_extension}"
    equal = True
    f_slice_name = f"{id_}{file_extension}"
    f_slice_path = f"./{f_slice_name}"
    f_slice = open(f_slice_path, 'wb')
    for i in range(len(urls)):
        url = urls[i]['url']
        res = requests.request("GET", url, headers=get_headers())
        print(res.text)

        f_slice.write(res.content)
    f_slice = None
    f = None
    if file_type == "variant":
        f_slice = VariantFile(f_slice_path)
        f = VariantFile(f"{LOCAL_FILE_PATH}/{f_name}")
    elif file_type == "read":
        f_slice = AlignmentFile(f_slice_path)
        f = AlignmentFile(f"{LOCAL_FILE_PATH}/{f_name}")

    # get start index for original file
    for rec in f_slice.fetch():
        f_index = rec.pos - 1
        break
    # compare slice and file line by line
    if 'referenceName' in params:
        zipped = zip(f_slice.fetch(), f.fetch(contig=params['referenceName'], start=f_index))
    else:
        zipped = zip(f_slice.fetch(), f.fetch())
    for x, y in zipped:
        if x != y:
            equal = False
            assert equal
    os.remove(f_slice_path)
    assert equal

def test_get_read_header():
    """
    A header of a SAM file should contain at least one @SQ line
    """
    url = f"{HOST}/htsget/v1/reads/data/NA02102?class=header&format=SAM"
    res = requests.request("GET", url, headers=get_headers())
    print(res.text)
    for line in res.iter_lines():
        if "@SQ" in line.decode("utf-8"):
            assert True
            return
    assert False


def search_variants():
    return [
        ({
            'headers': [
                'bcftools_viewVersion=1.4.1+htslib-1.4.1'
            ],
            'regions': [
                {
                    'referenceName': 'chr21',
                    'start': 48110000,
                    'end': 48120634
                }
            ]
        }, 1),
        ({
            'regions': [
                {
                    'referenceName': '20'
                }
            ]
        }, 1),
        ({
            'regions': [
                {
                    'referenceName': 'chr21',
                    'start': 48000000,
                    'end': 48120000
                },
                {
                    'referenceName': '21',
                    'start': 48110000,
                    'end': 48120634
                }
            ]
        }, 4)
    ]


@pytest.mark.parametrize('body, count', search_variants())
def test_search_variantfile(body, count):
    url = f"{HOST}/htsget/v1/variants/search"

    response = requests.post(url, json=body, headers=get_headers())
    print(response.text)
    assert len(response.json()["results"]) == count


def test_search_snp():
    url = f"{HOST}/htsget/v1/variants/search"
    body = {
            'regions': [
                {
                    'referenceName': 'chr21',
                    'start': 48062672,
                    'end': 48062673
                }
            ]
        }
    response = requests.post(url, json=body, headers=get_headers())
    print(response.text)
    assert len(response.json()["results"]) == 1


def get_multisamples():
    return [
        ({
            'regions': [
                {
                    'referenceName': 'chr21',
                    'start': 5030000,
                    'end': 5032000
                }
            ]
        }, 2)
    ]


@pytest.mark.parametrize('body, count', get_multisamples())
# The two multisample files both have two identically-named samples in them:
# both files should return two samples
def test_multisample(body, count):
    url = f"{HOST}/htsget/v1/variants/search"

    response = requests.post(url, json=body, headers=get_headers())
    print(response.text)
    for result in response.json()["results"]:
        assert len(result['samples']) == count


# There should be two BRCA genes in the database:
def test_gene_search():
    url = f"{HOST}/htsget/v1/genes/BRCA"

    response = requests.get(url, headers=get_headers())
    print(response.text)
    assert len(response.json()['results']) == 2


@pytest.fixture
def drs_objects():
    return [
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "NA18537.vcf.gz.tbi",
            "mime_type": "application/octet-stream",
            "name": "NA18537.vcf.gz.tbi",
            "self_uri": "drs://localhost/NA18537.vcf.gz.tbi",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "NA18537.vcf.gz",
            "mime_type": "application/octet-stream",
            "name": "NA18537.vcf.gz",
            "self_uri": "drs://localhost/NA18537.vcf.gz",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "contents": [
                {
                  "drs_uri": [
                      "drs://localhost/NA18537.vcf.gz"
                  ],
                  "name": "NA18537.vcf.gz",
                  "id": "variant"
                },
                {
                  "drs_uri": [
                      "drs://localhost/NA18537.vcf.gz.tbi"
                  ],
                  "name": "NA18537.vcf.gz.tbi",
                  "id": "index"
                }
            ],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "NA18537",
            "mime_type": "application/octet-stream",
            "name": "NA18537",
            "self_uri": "drs://localhost/NA18537",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "multisample_1.vcf.gz.tbi",
            "mime_type": "application/octet-stream",
            "name": "multisample_1.vcf.gz.tbi",
            "self_uri": "drs://localhost/multisample_1.vcf.gz.tbi",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "multisample_1.vcf.gz",
            "mime_type": "application/octet-stream",
            "name": "multisample_1.vcf.gz",
            "self_uri": "drs://localhost/multisample_1.vcf.gz",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "contents": [
                {
                    "drs_uri": [
                        "drs://localhost/multisample_1.vcf.gz"
                    ],
                    "name": "multisample_1.vcf.gz",
                    "id": "variant"
                },
                {
                    "drs_uri": [
                        "drs://localhost/multisample_1.vcf.gz.tbi"
                    ],
                    "name": "multisample_1.vcf.gz.tbi",
                    "id": "index"
                }
            ],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "multisample_1",
            "mime_type": "application/octet-stream",
            "name": "multisample_1",
            "self_uri": "drs://localhost/multisample_1",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "multisample_2.vcf.gz.tbi",
            "mime_type": "application/octet-stream",
            "name": "multisample_2.vcf.gz.tbi",
            "self_uri": "drs://localhost/multisample_2.vcf.gz.tbi",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "multisample_2.vcf.gz",
            "mime_type": "application/octet-stream",
            "name": "multisample_2.vcf.gz",
            "self_uri": "drs://localhost/multisample_2.vcf.gz",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "contents": [
                {
                    "drs_uri": [
                        "drs://localhost/multisample_2.vcf.gz"
                    ],
                    "name": "multisample_2.vcf.gz",
                    "id": "variant"
                },
                {
                    "drs_uri": [
                        "drs://localhost/multisample_2.vcf.gz.tbi"
                    ],
                    "name": "multisample_2.vcf.gz.tbi",
                    "id": "index"
                }
            ],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "multisample_2",
            "mime_type": "application/octet-stream",
            "name": "multisample_2",
            "self_uri": "drs://localhost/multisample_2",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "sample.compressed.vcf.gz.tbi",
            "mime_type": "application/octet-stream",
            "name": "sample.compressed.vcf.gz.tbi",
            "self_uri": "drs://localhost/sample.compressed.vcf.gz.tbi",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "sample.compressed.vcf.gz",
            "mime_type": "application/octet-stream",
            "name": "sample.compressed.vcf.gz",
            "self_uri": "drs://localhost/sample.compressed.vcf.gz",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "contents": [
                {
                    "drs_uri": [
                        "drs://localhost/sample.compressed.vcf.gz"
                    ],
                    "name": "sample.compressed.vcf.gz",
                    "id": "variant"
                },
                {
                    "drs_uri": [
                        "drs://localhost/sample.compressed.vcf.gz.tbi"
                    ],
                    "name": "sample.compressed.vcf.gz.tbi",
                    "id": "index"
                }
            ],
            "created_time": "2021-09-27T18:40:00.538843",
            "description": "",
            "id": "sample.compressed",
            "mime_type": "application/octet-stream",
            "name": "sample.compressed",
            "self_uri": "drs://localhost/sample.compressed",
            "size": 0,
            "updated_time": "2021-09-27T18:40:00.539022",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:58:56.663378",
            "description": "",
            "id": "NA20787.vcf.gz.tbi",
            "mime_type": "application/octet-stream",
            "name": "NA20787.vcf.gz.tbi",
            "self_uri": "drs://localhost/NA20787.vcf.gz.tbi",
            "size": 0,
            "updated_time": "2021-09-27T18:58:56.663442",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:58:56.663378",
            "description": "",
            "id": "NA20787.vcf.gz",
            "mime_type": "application/octet-stream",
            "name": "NA20787.vcf.gz",
            "self_uri": "drs://localhost/NA20787.vcf.gz",
            "size": 0,
            "updated_time": "2021-09-27T18:58:56.663442",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "contents": [
                {
                    "drs_uri": [
                        "drs://localhost/NA20787.vcf.gz"
                    ],
                    "name": "NA20787.vcf.gz",
                    "id": "variant"
                },
                {
                    "drs_uri": [
                       "drs://localhost/NA20787.vcf.gz.tbi"
                    ],
                    "name": "NA20787.vcf.gz.tbi",
                    "id": "index"
                }
            ],
            "created_time": "2021-09-27T18:58:56.663378",
            "description": "",
            "id": "NA20787",
            "mime_type": "application/octet-stream",
            "name": "NA20787",
            "self_uri": "drs://localhost/NA20787",
            "size": 0,
            "updated_time": "2021-09-27T18:58:56.663442",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:58:56.663378",
            "description": "",
            "id": "NA02102.bam.bai",
            "mime_type": "application/octet-stream",
            "name": "NA02102.bam.bai",
            "self_uri": "drs://localhost/NA02102.bam.bai",
            "size": 0,
            "updated_time": "2021-09-27T18:58:56.663442",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "created_time": "2021-09-27T18:58:56.663378",
            "description": "",
            "id": "NA02102.bam",
            "mime_type": "application/octet-stream",
            "name": "NA02102.bam",
            "self_uri": "drs://localhost/NA02102.bam",
            "size": 0,
            "updated_time": "2021-09-27T18:58:56.663442",
            "version": "v1"
        },
        {
            "aliases": [],
            "checksums": [],
            "contents": [
                {
                    "drs_uri": [
                        "drs://localhost/NA02102.bam"
                    ],
                    "name": "NA02102.bam",
                    "id": "read"
                },
                {
                    "drs_uri": [
                        "drs://localhost/NA02102.bam.bai"
                    ],
                    "name": "NA02102.bam.bai",
                    "id": "index"
                }
            ],
            "created_time": "2021-09-27T18:58:56.663378",
            "description": "",
            "id": "NA02102",
            "mime_type": "application/octet-stream",
            "name": "NA02102",
            "self_uri": "drs://localhost/NA02102",
            "size": 0,
            "updated_time": "2021-09-27T18:58:56.663442",
            "version": "v1"
        }
    ]