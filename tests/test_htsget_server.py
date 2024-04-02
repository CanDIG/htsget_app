import json
import os
import re
import sys
import pytest
import requests
from pathlib import Path
from authx.auth import get_minio_client, get_access_token, store_aws_credential
from time import sleep

# assumes that we are running pytest from the repo directory
REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}/..")
sys.path.insert(0, os.path.abspath(f"{REPO_DIR}/htsget_server"))
LOCAL_FILE_PATH = os.path.abspath(f"{REPO_DIR}/data/files")
SERVER_LOCAL_DATA = os.getenv("SERVER_LOCAL_DATA", "/app/htsget_server/data")
from config import PORT

HOST = os.getenv("TESTENV_URL", f"http://localhost:{PORT}")
TEST_KEY = os.environ.get("HTSGET_TEST_KEY")
USERNAME = os.getenv("CANDIG_SITE_ADMIN_USER")
PASSWORD = os.getenv("CANDIG_SITE_ADMIN_PASSWORD")
MINIO_URL = os.getenv("MINIO_URL")
VAULT_URL = os.getenv("VAULT_URL")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
CWD = os.getcwd()


def get_headers(username=USERNAME, password=PASSWORD):
    headers = {}
    try:
        token = get_access_token(username=username, password=password)
        headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        headers["Authorization"] = f"Bearer {TEST_KEY}"
    return headers


def test_remove_objects(cohorts):
    headers = get_headers()
    candig_url = os.getenv("CANDIG_URL")

    for cohort in cohorts:
        if candig_url is not None:
            response = requests.delete(f"{candig_url}/ingest/program/{cohort}", headers=get_headers())

        url = f"{HOST}/ga4gh/drs/v1/cohorts/{cohort}"
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            response = requests.request("DELETE", url, headers=headers)
            print(f"DELETE {cohort}: {response.text}")
            assert response.status_code == 200
        url = f"{HOST}/ga4gh/drs/v1/objects"
        response = requests.request("GET", url, headers=headers, params={"cohort_id": cohort})
        assert response.status_code == 200
        for obj in response.json():
            assert obj["cohort"] != cohort


def test_post_objects(drs_objects, cohorts):
    """
    Install test objects. Will fail if any post request returns an error.
    """
    # clean up old objects in db:
    url = f"{HOST}/ga4gh/drs/v1/objects"
    headers = get_headers()
    candig_url = os.getenv("CANDIG_URL")

    for cohort in cohorts:
        if candig_url is not None:
            test_program = {
                "program_id": cohort,
                "program_curators": [f"{USERNAME}@test.ca"],
                "team_members": [f"{USERNAME}@test.ca"]
            }

            response = requests.post(f"{candig_url}/ingest/program", headers=get_headers(), json=test_program)
            print(response.text)

    response = requests.request("GET", url, headers=headers)

    for obj in drs_objects:
        url = f"{HOST}/ga4gh/drs/v1/objects"
        response = requests.request("POST", url, json=obj, headers=headers)
        print(f"POST {obj}: {response.text}")
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
    access_url = f"file:///{SERVER_LOCAL_DATA}/files/NA18537.vcf.gz" # this is local within the htsget server container, not from where we're running pytest
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
    return [('sample.compressed'), ('NA18537'), ('multisample_1'), ('multisample_2'), ('test')]


@pytest.mark.parametrize('sample', index_variants())
def test_index_variantfile(sample):
    url = f"{HOST}/htsget/v1/variants/{sample}/index"
    params = {}
    params['force'] = True
    response = requests.get(url, params=params, headers=get_headers())
    assert response.status_code == 200

    # shouldn't take more than a second to index the tiny file, but just in case: a max 30 second check
    for i in range(30):
        get_url = f"{HOST}/ga4gh/drs/v1/objects/{sample}"
        response = requests.get(get_url, headers=get_headers())
        if response.status_code == 500:
            # in case indexing is still using the database, keep looping
            continue
        print(response.text)
        if response.json()["indexed"] == 1:
            break
        sleep(1)

    get_url = f"{HOST}/ga4gh/drs/v1/objects/{sample}"
    response = requests.get(get_url, headers=get_headers())
    print(response.text)
    assert response.json()["indexed"] == 1
    assert len(response.json()["checksums"]) > 0
    assert response.json()["size"] > 0


def test_install_public_object():
# s3://1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz
    headers = get_headers()
    try:
        token = get_access_token(username=USERNAME, password=PASSWORD)
    except Exception as e:
        token = None
    client = get_minio_client(token=token, s3_endpoint="http://s3.us-east-1.amazonaws.com", bucket="1000genomes", access_key=None, secret_key=None, public=True)
    access_id = f"{client['endpoint']}/{client['bucket']}"
    drs_url = HOST.replace("http://", "drs://").replace("https://", "drs://")
    pieces = [
        {
            "aliases": [],
            "checksums": [],
            "description": "index",
            "id": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi",
            "mime_type": "application/octet-stream",
            "name": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi",
            "size": 0,
            "version": "v1",
            "cohort": "1000genomes",
            "access_methods": [
                {
                    "type": "s3",
                    "access_id": f"{access_id}/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi?public=true"
                }
            ]
        },
        {
            "aliases": [],
            "checksums": [],
            "description": "variant",
            "id": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz",
            "mime_type": "application/octet-stream",
            "name": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz",
            "size": 0,
            "version": "v1",
            "cohort": "1000genomes",
            "access_methods": [
                {
                    "type": "s3",
                    "access_id": f"{access_id}/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz?public=true"
                }
            ]
        },
        {
            "aliases": [],
            "checksums": [],
            "contents": [
              {
                "drs_uri": [
                  f"{drs_url}/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz"
                ],
                "name": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz",
                "id": "variant"
              },
              {
                "drs_uri": [
                  f"{drs_url}/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi"
                ],
                "name": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz.tbi",
                "id": "index"
              }
            ],
            "description": "wgs",
            "reference_genome": "hg38",
            "id": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes",
            "mime_type": "application/octet-stream",
            "name": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes",
            "size": 0,
            "version": "v1",
            "cohort": "1000genomes"
        }
    ]
    for obj in pieces:
        url = f"{HOST}/ga4gh/drs/v1/objects"
        response = requests.request("POST", url, json=obj, headers=headers)
        print(f"POST {obj['name']}: {response.text}")
        assert response.status_code == 200


def get_ingest_file():
    return [
        (
            {
                "genomic_id": "NA18537",
                "samples": [
                    {
                        "sample_registration_id": "NA18537-wgs",
                        "sample_name_in_file": "NA18537"
                    }
                ]
            }, "1000genomes"
        )
    ]


def get_ingest_sample_names(genomic_id):
    result = {}
    for item in get_ingest_file():
        ingest_map, program_id = item
        if ingest_map["genomic_id"] == genomic_id:
            for sample in ingest_map["samples"]:
                result[sample['sample_name_in_file']] = f"{sample['sample_registration_id']}"
    return result


@pytest.mark.parametrize('input, program_id', get_ingest_file())
def test_add_sample_drs(input, program_id):
    post_url = f"{HOST}/ga4gh/drs/v1/objects"
    headers = get_headers()

    # look for the main genomic drs object
    get_url = f"{HOST}/ga4gh/drs/v1/objects/{input['genomic_id']}"
    response = requests.request("GET", get_url, headers=headers)
    if response.status_code == 200:
        assert response.status_code == 200
    genomic_drs_obj = response.json()
    contents_count = len(genomic_drs_obj["contents"])

    drs_url = HOST.replace("http://", "drs://").replace("https://", "drs://")
    for sample in input['samples']:
        sample_id = f"{sample['sample_registration_id']}"
        # remove any existing objects:
        sample_url = f"{HOST}/ga4gh/drs/v1/objects/{sample_id}"
        response = requests.request("GET", sample_url, headers=headers)
        if response.status_code == 200:
            response = requests.request("DELETE", sample_url, headers=headers)
            print(f"DELETE {sample_id}: {response.text}")
            assert response.status_code == 200

        # create a sampledrsobject to correspond to each sample:
        sample_drs_object = {
            "id": sample_id,
            "description": "sample",
            "contents": [
                {
                    "drs_uri": [
                        f"{drs_url}/{input['genomic_id']}"
                    ],
                    "name": sample['sample_name_in_file'],
                    "id": input['genomic_id']
                }
            ],
            "version": "v1",
            "cohort": program_id
        }
        response = requests.request("POST", post_url, json=sample_drs_object, headers=headers)
        print(f"POST {sample_drs_object['id']}: {response.text}")
        assert response.status_code == 200

        # add the sample contents to the genomic_drs_object's contents
        sample_contents = {
            "drs_uri": [
                f"{drs_url}/{sample_id}"
            ],
            "name": sample_id,
            "id": sample['sample_name_in_file']
        }
        genomic_drs_obj["contents"].append(sample_contents)

    response = requests.post(post_url, json=genomic_drs_obj, headers=get_headers())
    print(response.text)
    response = requests.request("GET", get_url, headers=headers)
    if response.status_code == 200:
        assert response.status_code == 200
    assert len(genomic_drs_obj["contents"]) == contents_count + 1

    verify_url = f"{HOST}/htsget/v1/variants/{input['genomic_id']}/verify"
    response = requests.get(verify_url)
    assert response.status_code == 200


@pytest.mark.parametrize('input, program_id', get_ingest_file())
def test_sample_stats(input, program_id):
    headers = get_headers()

    sample = get_ingest_sample_names(input['genomic_id'])
    print(sample)
    # look for the sample
    get_url = f"{HOST}/htsget/v1/samples/{sample[list(sample.keys()).pop()]}"
    response = requests.request("GET", get_url, headers=headers)
    if response.status_code == 200:
        assert response.status_code == 200

    assert input['genomic_id'] in response.json()['genomes']


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
         {'referenceName': 21, 'start': 10002800, 'end': 10050000},
         200),
        ('NA18537', 'variants',
         {'referenceName': 21},
         200),
        ('NA18537', 'variants',
         {'start': 10002800, 'end': 10050000},
         200),
        ('NA18537', 'variants', {}, 200),
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
        ({"referenceName": "19",
          "start": 0, "end": 1260000}, 'sample.compressed', ".vcf.gz", "variant", 2),
        ({}, 'sample.compressed', ".vcf.gz", "variant", 9),
        ({"referenceName": "21",
          "start": 10002800, "end": 10087068}, 'NA18537', ".vcf.gz", "variant", 18)
    ]


@pytest.mark.parametrize('params, id_, file_extension, file_type, count', pull_slices_data())
def test_pull_slices(params, id_, file_extension, file_type, count):
    params['class'] = 'body'
    url = f"{HOST}/htsget/v1/{file_type}s/data/{id_}"
    res = requests.request("GET", url, params=params, headers=get_headers())
    lines = res.text.rstrip().split('\n')
    print(lines)
    assert count == len(lines)


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


# There should be two BRCA genes in the database:
def test_gene_search():
    url = f"{HOST}/htsget/v1/genes/BRCA"

    response = requests.get(url, headers=get_headers())
    print(response.text)
    assert len(response.json()['results']) == 2


def test_beacon_get_search():
    # for an authed user, this short allele form request should work:
    # return two variations, one ref, one alt, for a single position.
    url = f"{HOST}/beacon/v2/g_variants?assemblyId=hg38&allele=NC_000021.9%3Ag.5030847T%3EA"
    response = requests.get(url, headers=get_headers())
    print(response.text)
    assert len(response.json()['response']) == 2


def get_beacon_post_search():
    return [
        (
            # 6 variations, corresponding to three variant records in multisample_1 and multisample_2
            # first variation, corresponding to "NC_000021.8:g.5030551=", should contain two cases
            {
                "query": {
                    "requestParameters": {
                        "start": [5030000],
                        "end": [5030847],
                        "assemblyId": "hg38",
                        "referenceName": "21"
                    }
                },
                "meta": {
                    "apiVersion": "v2"
                }
            }, 6, 2
        ),
        (
            # 5 variations, corresponding to 2 refs and 3 alts in test
            # first variation has two cases
            {
                "query": {
                    "requestParameters": {
                        "start": [16562322],
                        "end": [16613564],
                        "referenceName": "1"
                    }
                },
                "meta": {
                    "apiVersion": "v2"
                }
            }, 5, 2
        )
    ]


@pytest.mark.parametrize('body, count, cases', get_beacon_post_search())
def test_beacon_post_search(body, count, cases):
    url = f"{HOST}/beacon/v2/g_variants"

    response = requests.post(url, json=body, headers=get_headers())
    print(response.text)
    assert len(response.json()['response']) == count
    assert len(response.json()['response'][0]['caseLevelData']) == cases


# if we search for NBPF1, we should find records in test.vcf that contain NBPF1 in their VEP annotations.
def test_beacon_search_annotations():
    url = f"{HOST}/beacon/v2/g_variants"
    body = {
        "query": {
            "requestParameters": {
                "gene_id": 'NBPF1'
            }
        },
        "meta": {
            "apiVersion": "v2"
        }
    }
    response = requests.post(url, json=body, headers=get_headers())
    found_gene = False
    print(response.json())
    for var in response.json()['response']:
        if 'molecularAttributes' in var:
            if 'geneIds' in var['molecularAttributes']:
                print(var['molecularAttributes']['geneIds'])
                if 'NBPF1' in var['molecularAttributes']['geneIds']:
                    found_gene = True
    assert found_gene


def test_vcf_json():
    params = {'format': 'VCF-JSON'}
    url = f"{HOST}/htsget/v1/variants/data/test"
    res = requests.request("GET", url, params=params, headers=get_headers())
    assert res.json()['id'] == 'test'
    assert len(res.json()['variants']) == 7


@pytest.fixture
def cohorts():
    return ["test-htsget", "1000genomes"]


@pytest.fixture
def drs_objects():
    drs_objects = {}
    for root, dirs, files in os.walk(LOCAL_FILE_PATH):
        for f in files:
            print(f)
            name_match = re.match(r"^(.+?)\.(vcf|vcf\.gz|bcf|bcf\.gz|sam|bam)(\.tbi|\.bai)*$", f)
            if name_match is not None:
                genomic_id = name_match.group(1)
                if genomic_id not in drs_objects:
                    drs_objects[genomic_id] = {}
                if name_match.group(3) is not None:
                    drs_objects[genomic_id]["index"] = name_match.group(0)
                else:
                    key = "variant"
                    if name_match.group(2) in ["sam", "bam"]:
                        key = "read"
                    drs_objects[genomic_id][key] = name_match.group(0)
        break
    result = []
    drs_url = HOST.replace("http://", "drs://").replace("https://", "drs://")
    for drs_obj in drs_objects:
        # make a genomicdrsobj:
        genomic_drs_obj = {
            "id": drs_obj,
            "description": "wgs",
            "mime_type": "application/octet-stream",
            "name": drs_obj,
            "contents": [],
            "version": "v1",
            "reference_genome": "hg38",
            "cohort": "test-htsget"
        }
        result.append(genomic_drs_obj)

        # make a genomicindexdrsobj:
        index_file = drs_objects[drs_obj].pop("index")
        result.append({
            "id": index_file,
            "description": "index",
            "mime_type": "application/octet-stream",
            "name": index_file,
            "version": "v1",
            "cohort": "test-htsget"
        })
        # add it to the contents of the genomic_drs_obj:
        genomic_drs_obj['contents'].append({
            "drs_uri": [
                f"{drs_url}/{index_file}"
            ],
            "name": index_file,
            "id": "index"
        })

        # make a genomicdatadrsobj:
        type = list(drs_objects[drs_obj].keys()).pop()
        data_file = drs_objects[drs_obj].pop(type)
        result.append({
            "id": data_file,
            "description": type,
            "mime_type": "application/octet-stream",
            "name": data_file,
            "version": "v1",
            "cohort": "test-htsget"
        })
        # add it to the contents of the genomic_drs_obj:
        genomic_drs_obj['contents'].append({
            "drs_uri": [
                f"{drs_url}/{data_file}"
            ],
            "name": data_file,
            "id": type
        })

    client = get_client()

    for obj in result:
        if "contents" not in obj:
            # create access_methods:
            access_id = f"{client['endpoint']}/{client['bucket']}/{obj['id']}"
            if VAULT_URL is None and client['access'] and client['secret']:
                access_id += f"?access={client['access']}&secret={client['secret']}"
            obj["access_methods"] = [
                {
                    "type": "s3",
                    "access_id": access_id
                }
            ]
            try:
                file = Path(LOCAL_FILE_PATH).joinpath(obj['id'])
                obj['size'] = file.stat().st_size
                with Path.open(file, "rb") as fp:
                    res = client['client'].put_object(client['bucket'], obj['id'], fp, file.stat().st_size)
            except Exception as e:
                print(str(e))
                assert False
                return {"message": str(e)}, 500
    return result


def get_client():
        # in case we're running on the container itself, which might have secrets
        try:
            with open("/run/secrets/minio-access-key", "r") as f:
                minio_access_key = f.read().strip()
        except Exception as e:
            minio_access_key = MINIO_ACCESS_KEY
        try:
            with open("/run/secrets/minio-secret-key", "r") as f:
                minio_secret_key = f.read().strip()
        except Exception as e:
            minio_secret_key = MINIO_SECRET_KEY

        client = None
        try:
            bucket = 'testhtsget'
            if MINIO_URL and minio_access_key and minio_secret_key:
                if VAULT_URL:
                    token = get_access_token(username=USERNAME, password=PASSWORD)
                    credential, status_code = store_aws_credential(token=token, endpoint=MINIO_URL, bucket=bucket, access=minio_access_key, secret=minio_secret_key, vault_url=VAULT_URL)
                    if status_code == 200:
                        client = get_minio_client(token=token, s3_endpoint=credential["endpoint"], bucket=bucket)
                else:
                    client = get_minio_client(token=None, s3_endpoint=MINIO_URL, bucket=bucket, access_key=minio_access_key, secret_key=minio_secret_key)
            if client is None:
                client = get_minio_client(bucket=bucket)
        except Exception as e:
            print(str(e))
            assert False
            return {"message": str(e)}, 500

        return client
