from minio import Minio
from minio.error import (ResponseError, BucketAlreadyOwnedByYou,BucketAlreadyExists)
from pysam import VariantFile
import json

# Initialize minioClient with an endpoint and access/secret keys.
minioClient = Minio('play.min.io:9000',
                    access_key='Q3AM3UQ867SPQQA43P2F',
                    secret_key='zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG',
                    secure=True)

def create_bucket():
    # Make a bucket with the make_bucket API call.
    try:
        minioClient.make_bucket("miniotest", location="us-east-1")
        print("made bucket")
    except BucketAlreadyOwnedByYou as err:
        print("bucket owned")
        pass
    except BucketAlreadyExists as err:
        print("Bucket already exists") 
        pass
    except ResponseError as err:
        raise
    else:
            # Put an object 'pumaserver_debug.log' with contents from 'pumaserver_debug.log'.
            print("else statement")
            try:
                minioClient.fput_object('maylogs', 'pumaserver_debug.log', '/tmp/pumaserver_debug.log')
            except ResponseError as err:
                print(err)

def upload_file():
    try:
        minioClient.fput_object('test', 'NA18537.vcf.gz.tbi', '../../data/files/NA18537.vcf.gz.tbi')
    except ResponseError as err:
        print(err)

def download_file():
    try:
        data = minioClient.fget_object('test', 'NA18537.vcf.gz.tbi', '../data/files/test.vcf.gz')
        print(data.object_name)
    except ResponseError as err:
        print(err)


def download_file_2():
    try:
        data = minioClient.get_object('test', 'NA18537.vcf.gz.tbi')
        # raw_data = data.read()
        # encoding = data.info().get_content_charset('utf8')
        # data = json.loads(raw_data.decode(encoding))
        vcf_in = VariantFile("-", "wb")
        for s in data.stream():
            vcf_in.write(s)
        # for rec in vcf.fetch():
        #     print(rec.pos)
        # for d in data.stream():
        #     print(d)
    except ResponseError as err:
        print(err)


# download_file()
# upload_file()
download_file_2()
