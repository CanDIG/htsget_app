import json
import os
import re
import sys
import pytest
import requests
from pathlib import Path
from authx.auth import get_minio_client, get_site_admin_token, store_aws_credential
from time import sleep

# assumes that we are running pytest from the repo directory
REPO_DIR = os.path.abspath(f"{os.path.dirname(os.path.realpath(__file__))}/..")
sys.path.insert(0, os.path.abspath(f"{REPO_DIR}/htsget_server"))
LOCAL_FILE_PATH = os.path.abspath(f"{REPO_DIR}/data/files")
SERVER_LOCAL_DATA = os.getenv("SERVER_LOCAL_DATA", "/app/htsget_server/data")

HOST = os.getenv("TESTENV_URL")
TEST_KEY = os.getenv("HTSGET_TEST_KEY")
USERNAME = os.getenv("CANDIG_NOT_ADMIN_USER2", "user2@test.ca")
MINIO_URL = os.getenv("MINIO_URL")
VAULT_URL = os.getenv("VAULT_URL")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
CWD = os.getcwd()


def get_headers():
    headers = {}
    if TEST_KEY is not None:
        headers["Authorization"] = f"Bearer {TEST_KEY}"
        return headers
    try:
        token = get_site_admin_token()
        headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        headers["Authorization"] = f"Bearer {TEST_KEY}"
    return headers


def test_indexer_on():
    headers = get_headers()
    url = f"{HOST}/htsget/v1/indexer"
    response = requests.request("GET", url, headers=headers)
    if response.status_code == 200:
        assert response.json()['status'] == "ON"


def remove_programs(programs):
    headers = get_headers()
    candig_url = os.getenv("CANDIG_URL")

    for program in programs:
        if candig_url is not None:
            response = requests.delete(f"{candig_url}/ingest/program/{program}", headers=get_headers())

        url = f"{HOST}/ga4gh/drs/v1/programs/{program}"
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            response = requests.request("DELETE", url, headers=headers)
            print(f"DELETE {program}: {response.text}")
            assert response.status_code == 200
        url = f"{HOST}/ga4gh/drs/v1/objects"
        response = requests.request("GET", url, headers=headers, params={"program_id": program})
        print(response.text)
        assert response.status_code == 200
        for obj in response.json():
            assert obj["program"] != program


def test_post_objects(drs_objects, programs):
    """
    Install test objects. Will fail if any post request returns an error.
    """
    # clean up old objects in db:
    remove_programs(programs)

    url = f"{HOST}/ga4gh/drs/v1/objects"
    headers = get_headers()
    candig_url = os.getenv("CANDIG_URL")

    for program in programs:
        if candig_url is not None:
            test_program = {
                "program_id": program,
                "program_curators": [USERNAME],
                "team_members": [USERNAME]
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


def test_install_public_object():
# s3://1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes.vcf.gz
    headers = get_headers()
    try:
        token = get_site_admin_token()
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
            "program": "1000genomes",
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
            "program": "1000genomes",
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
            "description": "sequence_variation",
            "reference_genome": "hg38",
            "id": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes",
            "mime_type": "application/octet-stream",
            "name": "ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes",
            "size": 0,
            "version": "v1",
            "program": "1000genomes"
        }
    ]
    for obj in pieces:
        url = f"{HOST}/ga4gh/drs/v1/objects"
        response = requests.request("POST", url, json=obj, headers=headers)
        print(f"POST {obj['name']}: {response.text}")
        assert response.status_code == 200

    # check to make sure we can get data from this
    url = f"{HOST}/htsget/v1/variants/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes"
    response = requests.request("GET", url, headers=headers)
    assert response.status_code == 200

    url = f"{HOST}/htsget/v1/variants/data/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5a.20130502.genotypes?class=header"
    response = requests.request("GET", url, headers=headers)
    assert response.status_code == 200

    assert response.text.startswith("##fileformat=VCFv4.1")


def index_variants():
    return [('sample.compressed'), ('NA18537'), ('multisample_1'), ('multisample_2'), ('test')]


@pytest.mark.parametrize('sample', index_variants())
def test_index_variantfile(sample):
    url = f"{HOST}/htsget/v1/{sample}/index"
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
    # comment these out since we don't calculate checksums or sizes anymore
    # assert len(response.json()["checksums"]) > 0
    # assert response.json()["size"] > 0

def get_ingest_file():
    return [
        (
            {
                "program_id": "1000genomes",
                "experiment_id": "LOCAL-SEQ_0090",
                "submitter_sample_id": "NA18537-wgs",
                "metadata": {
                    "library_strategy": "WGS"
                }
            },
            {
                "program_id": "1000genomes",
                "analysis_id": "NA18537",
                "analysis_sample_id": "NA18537",
                "experiment_id": "NA18537-wgs"
            }
        )
    ]


def get_ingest_experiment_names(genomic_id):
    result = {}
    for item in get_ingest_file():
        ingest_map, program_id = item
        if ingest_map["genomic_id"] == genomic_id:
            for sample in ingest_map["samples"]:
                result[sample['sample_registration_id']] = f"{sample['sample_name_in_file']}"
    return result


@pytest.mark.parametrize('experiment, analysis', get_ingest_file())
def test_add_experiment_drs(experiment, analysis):
    post_url = f"{HOST}/ga4gh/drs/v1/objects"
    headers = get_headers()

    # look for the main analysis drs object
    get_url = f"{HOST}/ga4gh/drs/v1/objects/{analysis['analysis_id']}"
    response = requests.request("GET", get_url, headers=headers)
    if response.status_code == 200:
        assert response.status_code == 200
    analysis_drs_obj = response.json()
    contents_count = len(analysis_drs_obj["contents"])

    drs_url = HOST.replace("http://", "drs://").replace("https://", "drs://")

    # create a experimentdrsobject to correspond to each experiment:
    experiment_drs_object = {
        "id": experiment['experiment_id'],
        "name": experiment["submitter_sample_id"],
        "description": "wgs",
        "program": experiment['program_id'],
        "contents": [
            {
                "drs_uri": [
                    f"{drs_url}/{analysis['analysis_id']}"
                ],
                "name": analysis['analysis_sample_id'],
                "id": analysis['analysis_id']
            }
        ],
        "version": "v1",
        "metadata": {}
    }
    response = requests.request("POST", post_url, json=experiment_drs_object, headers=headers)
    print(f"POST {experiment_drs_object['id']}: {response.text}")
    assert response.status_code == 200

    # add the experiment contents to the analysis_drs_object's contents
    experiment_contents = {
        "drs_uri": [
            f"{drs_url}/{experiment['experiment_id']}"
        ],
        "name": experiment['experiment_id'],
        "id": analysis['analysis_sample_id']
    }
    analysis_drs_obj["contents"].append(experiment_contents)

    response = requests.post(post_url, json=analysis_drs_obj, headers=get_headers())
    print(response.text)
    response = requests.request("GET", get_url, headers=get_headers())
    if response.status_code == 200:
        assert response.status_code == 200
    assert len(analysis_drs_obj["contents"]) == contents_count + 1

    verify_url = f"{HOST}/htsget/v1/{analysis["analysis_id"]}/verify"
    response = requests.get(verify_url, headers=get_headers())
    print(response.text)
    assert response.status_code == 200


@pytest.mark.parametrize('experiment, analysis', get_ingest_file())
def test_experiment_stats(experiment, analysis):
    headers = get_headers()

    experiment = experiment['experiment_id']
    # look for the experiment
    get_url = f"{HOST}/htsget/v1/experiments/{experiment}"
    response = requests.request("GET", get_url, headers=headers)
    assert response.status_code == 200

    # genomes in a program will be experiments, which are listed by sample_registration_id
    assert experiment in response.json()['genomes']


def test_program_experiments():
    headers = get_headers()

    get_url = f"{HOST}/htsget/v1/experiments"
    response = requests.request("GET", get_url, headers=headers)
    print(response.json())
    response = requests.request("GET", get_url, headers=headers, params={"program": "1000genomes"})
    assert response.status_code == 200
    print(response.json())
    assert len(response.json()) == 1


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
    assert len(response.json()['estimatedResults']["test-htsget"]) == 2

    url = re.sub(r".+\/beacon\/v2", f"{HOST}/beacon/v2", response.json()['beaconResultUrl'])
    response = requests.get(url, headers=get_headers())
    tries = 0
    while response.status_code != 201:
        sleep(2)
        response = requests.get(url, headers=get_headers())
        print(response.json())
        tries = tries + 1
        if tries > 10:
            print("search is taking too long")
            assert False

    assert len(response.json()['response']) == 2


def get_beacon_post_search():
    return [
        (
            # 6 variations, corresponding to three variant records in multisample_1 and multisample_2
            # first variation, corresponding to "NC_000021.9:g.5030551=", should contain two cases
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

    url = re.sub(r".+\/beacon\/v2", f"{HOST}/beacon/v2", response.json()['beaconResultUrl'])
    response = requests.get(url, headers=get_headers())
    tries = 0
    while response.status_code != 201:
        sleep(2)
        response = requests.get(url, headers=get_headers())
        print(response.json())
        tries = tries + 1
        if tries > 10:
            print("search is taking too long")
            assert False

    assert len(response.json()['response']) == count
    assert len(response.json()['response'][0]['caseLevelData']) == cases


# if we search for NBPF1, we should find records in test.vcf that contain NBPF1 in their VEP annotations.
def test_beacon_search_annotations():
    url = f"{HOST}/beacon/v2/g_variants"
    body = {
        "query": {
            "requestParameters": {
                "gene_id": 'NBPF1',
                "full_search": True
            }
        },
        "meta": {
            "apiVersion": "v2"
        }
    }
    response = requests.post(url, json=body, headers=get_headers())

    url = re.sub(r".+\/beacon\/v2", f"{HOST}/beacon/v2", response.json()['beaconResultUrl'])
    response = requests.get(url, headers=get_headers())
    tries = 0
    while response.status_code != 201:
        sleep(2)
        response = requests.get(url, headers=get_headers())
        print(response.json())
        tries = tries + 1
        if tries > 10:
            print("search is taking too long")
            assert False

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


def test_remove_programs(programs):
    remove_programs(programs)


@pytest.fixture
def programs():
    return ["test-htsget", "1000genomes"]


@pytest.fixture
def drs_objects():
    drs_objects = {}
    for root, dirs, files in os.walk(LOCAL_FILE_PATH):
        for f in files:
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
        index_file = drs_objects[drs_obj].pop("index")
        type = list(drs_objects[drs_obj].keys()).pop()
        data_file = drs_objects[drs_obj].pop(type)

        # make a analysisdrsobj:
        analysis_drs_obj = {
            "id": drs_obj,
            "description": "analysis",
            "mime_type": "application/octet-stream",
            "name": drs_obj,
            "contents": [],
            "version": "v1",
            "reference_genome": "hg38",
            "program": "test-htsget"
        }
        result.append(analysis_drs_obj)

        result.append({
            "id": index_file,
            "description": "index",
            "mime_type": "application/octet-stream",
            "name": index_file,
            "version": "v1",
            "program": "test-htsget"
        })
        # add it to the contents of the analysis_drs_obj:
        analysis_drs_obj['contents'].append({
            "drs_uri": [
                f"{drs_url}/{index_file}"
            ],
            "name": index_file,
            "id": "index"
        })

        # make a analysisdatadrsobj:
        result.append({
            "id": data_file,
            "description": "analysis",
            "mime_type": "application/octet-stream",
            "name": data_file,
            "version": "v1",
            "program": "test-htsget"
        })
        # add it to the contents of the analysis_drs_obj:
        analysis_drs_obj['contents'].append({
            "drs_uri": [
                f"{drs_url}/{data_file}"
            ],
            "name": data_file,
            "id": type
        })

    for obj in result:
        if "contents" not in obj:
            access_url = f"file:///{SERVER_LOCAL_DATA}/files/{obj['id']}" # this is local within the htsget server container, not from where we're running pytest
            obj["access_methods"] = [
                {
                    "type": "file",
                    "access_url": {
                        "url": access_url
                    }
                }
            ]

    return result
