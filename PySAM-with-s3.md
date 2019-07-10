# Using PySAM to Access Signed S3 Bucket

PySAM is a python library which provides an interface for reading and writing read and variant files.The most common way of accessing a file is with a local file path. However, with S3 buckets emerging as a popular file storage system, it is natural that PySAM should be able to interact with a file referenced by a S3 path. PySAM is a wrapper of the htslib C-API which does support S3 paths, but many issues arose when my team and I tried to pass a s3 supported file in Minio to PySAM. The steps taken to successfully pass a s3 supported file in Minio to PySAM are addressed below.

## 1) Download and install htslib version from developer branch
   
We discovered that the latest release of htslib(1.9) does not support signed s3 buckets, but their developer branch does. The installation instructions can be found here: https://github.com/samtools/htslib 

## 2) Successfully open file from S3 path using htslib directly

After installing htslib from developer branch, we tested to see if htslib can call a s3 bucket, and if it works, then pointing PySAM to use this htslib should work as well. We used the testing server play.min.io and created our own test bucket called testfiles with the file NA18537.vcf.gz. 

To call a signed s3 bucket, we have to create a ./s3cfg file in the root directory of your computer. The file should look like this:
```
[default]
access_key = Q3AM3UQ867SPQQA43P2F  
secret_key = zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG  
host_base = min.io:9000
```

If you're wondering why the host_base is min.io:9000 and not play.min.io:9000, it is because htslib accepts the host_base in a specific format, and we had to play around with it for awhile to get it to read the host name in the way we wanted. In general, when calling the s3 path with htslib, the path is in the following format:

```
s3://<host_base>/<bucket-of-file>/<file-name>
``` 

After the ./s3cfg file is created, we used this command to open the file

```
htsfile s3://default@play/testfiles/NA18537.vcf.gz
```

If it was successful, the output would look something like this:
```
s3://default@play/testfiles/NA18537.vcf.gz:     VCF version 4.1 BGZF-compressed variant calling data
```
## 3) Rebuild PySAM from source
   