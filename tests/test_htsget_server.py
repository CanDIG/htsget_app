import os
import sys
import pytest
import requests
from pysam import AlignmentFile, VariantFile
from minio import Minio
from pathlib import Path

# assumes that we are running pytest from the repo directory
sys.path.insert(0,os.path.abspath("htsget_server"))
from config import PORT, LOCAL_FILE_PATH

HOST = f"http://localhost:{PORT}"
TEST_KEY = os.environ.get("HTSGET_TEST_KEY")
CWD = os.getcwd()
headers={"Test_Key": TEST_KEY, "Authorization": "Bearer testtest"}

def test_post_objects(drs_objects):
    """
    Install test objects. Will fail if any post request returns an error.
    """
    # clean up old objects in db:
    url = f"{HOST}/ga4gh/drs/v1/objects"
    response = requests.request("GET", url, headers=headers)
    for obj in drs_objects:
        url = f"{HOST}/ga4gh/drs/v1/objects/{obj['id']}"
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            response = requests.request("DELETE", url, headers=headers)
            print(f"DELETE {obj['name']}: {response.text}")
            assert response.status_code == 200
        if "access_methods" in obj and obj["access_methods"][0]["type"] == "s3":
            method = obj["access_methods"][0]
            client = Minio(
                "play.min.io:9000",
                access_key="Q3AM3UQ867SPQQA43P2F",
                secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
            )
            bucket = "testhtsget"
            try:
                #create the minio bucket/object/etc
                if not client.bucket_exists(bucket):
                    if 'region' in method:
                        client.make_bucket(bucket, location=method['region'])
                    else:
                        client.make_bucket(bucket)
                file = Path(LOCAL_FILE_PATH).joinpath(obj['id'])
                with Path.open(file, "rb") as fp:
                    result = client.put_object(bucket, obj['id'], fp, file.stat().st_size)
            except Exception as e:
                print(str(e))
                assert False
                return {"message": str(e)}, 500
        url = f"{HOST}/ga4gh/drs/v1/objects"
        response = requests.request("POST", url, json=obj, headers=headers)
        print(f"POST {obj['name']}: {response.json()}")
        assert response.status_code == 200

def test_post_update():
    url = f"{HOST}/ga4gh/drs/v1/objects"
    obj = {
    "access_methods": [
      {
        "access_url": {
          "url": f"file://{CWD}/data/files/NA18537.vcf.gz.tbi"
        },
        "type": "file"
      }
    ],
    "id": "NA18537.vcf.gz.tbi",
    "name": "NA18537.vcf.gz.tbi",
    "self_uri": "drs://localhost/NA18537.vcf.gz.tbi",
    "size": 100
  }
    response = requests.post(url, json=obj, headers=headers)
    assert response.json()["size"] == 100


def test_index_variants():
    return [('NA18537'), ('NA20787'), ('sample.compressed')]


@pytest.mark.parametrize('sample', test_index_variants())
def test_index_variantfile(sample):
    url = f"{HOST}/htsget/v1/variants/{sample}/index"
    params = None
    #params = {'force': True}
    response = requests.get(url, params=params, headers=headers)
    print(response.text)
    assert response.json()["id"] == sample


def invalid_start_end_data():
    return [(17123456, 23588), (9203, 42220938)]


@pytest.mark.parametrize('start, end', invalid_start_end_data())
def test_invalid_start_end(start, end):
    """
    Should return a 400 error if end is smaller than start
    """
    url_v = f"{HOST}/htsget/v1/variants/NA18537?referenceName=21&start={start}&end={end}"
    url_r = f"{HOST}/htsget/v1/reads/NA18537?referenceName=21&start={start}&end={end}"

    res_v = requests.request("GET", url_v, headers=headers)
    res_r = requests.request("GET", url_r, headers=headers)

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
    url_v = f"{HOST}/htsget/v1/variants/{id}?referenceName=21&start=10235878&end=45412368"
    url_r = f"{HOST}/htsget/v1/reads/{id}?referenceName=21&start=10235878&end=45412368"

    res_v = requests.request("GET", url_v, headers=headers)
    res_r = requests.request("GET", url_r, headers=headers)
    assert res_v.status_code == expected_status or res_r.status_code == expected_status


def test_file_without_start_end_data():
    return [('NA18537', '21', '.vcf.gz', 'variant'), ('NA20787', '21', '.vcf.gz', 'variant')]


def test_pull_slices_data():
    return [
        ({"referenceName": "21",
          "start": 92033, "end": 32345678}, 'NA18537', ".vcf.gz", "variant")
    ]


@pytest.mark.parametrize('params, id_, file_extension, file_type', test_pull_slices_data())
def test_pull_slices(params, id_, file_extension, file_type):
    url = f"{HOST}/htsget/v1/{file_type}s/{id_}"    
    res = requests.request("GET", url, params=params, headers=headers)
    res = res.json()    
    urls = res['htsget']['urls']

    f_index = 0
    f_name = f"{id_}{file_extension}"
    equal = True
    for i in range(len(urls)):
        url = urls[i]['url']
        res = requests.request("GET", url, headers=headers)

        f_slice_name = f"{id_}_{i}{file_extension}"
        f_slice_path = f"./{f_slice_name}"
        f_slice = open(f_slice_path, 'wb')
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
        for x, y in zip(f_slice.fetch(), f.fetch(contig=params['referenceName'], start=f_index)):
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
    res = requests.request("GET", url, headers=headers)
    for line in res.iter_lines():
        if "@SQ" in line.decode("utf-8"):
            assert True
            return
    assert False


def test_search_variants():
    return [
        {
            'headers': [
                'bcftools_viewVersion=1.4.1+htslib-1.4.1'
            ],
            'regions': [
                {
                    'referenceName': 'chr21',
                    'start': 48110083,
                    'end': 48120000
                }
            ]
        }, {
            'regions': [
                {
                    'referenceName': '20'
                }
            ]
        }, {
            'regions': [
                {
                    'referenceName': 'chr21',
                    'start': 48117000,
                    'end': 48120634
                }
            ]
        }
    ]


@pytest.mark.parametrize('body', test_search_variants())
def test_search_variantfile(body):
    url = f"{HOST}/htsget/v1/variants/search"
    
    response = requests.post(url, json=body, headers=headers)
    print(response.text)
    assert response.json()["htsget"] is not None

@pytest.fixture
def drs_objects():
    return [
  {
    "access_methods": [
      {
        "access_id": "play.min.io:9000/testhtsget/NA18537.vcf.gz.tbi",
        "type": "s3",
        "region": "us-east-1"
      }
    ],
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
    "access_methods": [
      {
        "access_id": "play.min.io:9000/testhtsget/NA18537.vcf.gz",
        "type": "s3",
        "region": "us-east-1"
      }
    ],
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
    "access_methods": [
      {
        "access_id": "play.min.io:9000/testhtsget/sample.compressed.vcf.gz.tbi",
        "type": "s3",
        "region": "us-east-1"
      }
    ],
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
    "access_methods": [
      {
        "access_id": "play.min.io:9000/testhtsget/sample.compressed.vcf.gz",
        "type": "s3",
        "region": "us-east-1"
      }
    ],
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
    "access_methods": [
      {
        "access_id": "play.min.io:9000/testhtsget/NA20787.vcf.gz.tbi",
        "type": "s3"
      }
    ],
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
    "access_methods": [
      {
        "access_id": "play.min.io:9000/testhtsget/NA20787.vcf.gz",
        "type": "s3"
      }
    ],
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
    "access_methods": [
      {
        "access_id": "play.min.io:9000/testhtsget/NA02102.bam.bai",
        "type": "s3"
      }
    ],
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
    "access_methods": [
      {
        "access_url": {
          "headers": [],
          "url": f"file://{CWD}/data/files/NA02102.bam"
        },
        "type": "file"
      }
    ],
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