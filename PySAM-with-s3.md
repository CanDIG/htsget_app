# Using PySAM to Access Signed S3 Bucket

I was working on a project for [CanDIG](https://www.distributedgenomics.ca/) which was an [Htsget API](https://github.com/CanDIG/htsget_app) implementation with two different file storage configurations. One was a local sqllite database and the other was using DRS and Minio. Minio is an object storage system and it is a great choice for security and scability of our htsget application. A main component of our application was the PySAM library which provides an interface for reading and writing read and variant files. The most common way of accessing a file is with a local file path. However, with S3 buckets emerging as a popular file storage system, it is natural that PySAM should be able to interact with a file referenced by a S3 path. PySAM is a wrapper of the htslib C-API which should support S3 paths, but many issues arose when my team and I tried to pass a s3 supported file in Minio to PySAM. After many google searches, there seems to be many people having issues accessing a s3 file path such as:
1) https://www.biostars.org/p/213305/
2) https://github.com/pysam-developers/pysam/issues/557
3) https://www.biostars.org/p/213305/ 

Although several sources claim that accessing a s3 file should just work, I have not been able to find a single worked example. After many days of digging on the web and coming across several problems, my team and I figured out how to successfully use PySAM and htslib to access a Signed S3 Bucket.

The steps taken to successfully pass a s3 supported file in Minio to PySAM are discussed below.

## 1) Download and install htslib version from developer branch
   
Although the current release of htslib should support s3 buckets, they do not support signed s3 buckets. We discovered that the latest release of htslib(1.9) does not support signed s3 buckets, but their developer branch does. The installation instructions can be found here: https://github.com/samtools/htslib . Make sure to add the --enable-s3 option during installation. 

To check whether htslib installed correctly, use the command:
```
which htsfile
```
The output should be:
```
/usr/local/bin/htsfile
```

## 2) Successfully open file from S3 path using htslib directly

After installing htslib from developer branch, we tested to see if htslib can call a s3 bucket, and if it works, then directing PySAM to use this htslib should work as well. We used the testing server play.min.io:9000 and created our own test bucket called testfiles with the file NA18537.vcf.gz. 

To call a signed s3 bucket, we have to create a ./s3cfg file in the root directory of your computer. The file should look like this:
```
[default]
access_key = Q3AM3UQ867SPQQA43P2F  
secret_key = zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG  
host_base = min.io:9000
```

If you're wondering why the host_base is min.io:9000 and not play.min.io:9000, it is because htslib reads the host_base, and the file path in a specific format, and we had to play around with it for awhile to get it to read the host name in the way we wanted. In general, when calling the s3 path with htslib, the path is in the following format:

```
s3://<host_base>@<bucket>/<another-bucket>/<file-name>
``` 

After the ./s3cfg file is created, we used this command to open the file

```
htsfile s3://default@play/testfiles/NA18537.vcf.gz
```

If the request was successful, the output would look something like this:
```
s3://default@play/testfiles/NA18537.vcf.gz:     VCF version 4.1 BGZF-compressed variant calling data
```

### If you got an error
If you got an error, you may want to run the command with -vvvvv to see a detailed log. Using the command from the example earlier: 
```
htsfile -vvvvv s3://default@play/testfiles/NA18537.vcf.gz
```
If successful, the output should look something like this:
```
[D::init_add_plugin] Loaded "knetfile"[D::init_add_plugin] Loaded "mem"
[D::init_add_plugin] Loaded "/usr/local/libexec/htslib/hfile_s3_write.so"
[D::init_add_plugin] Loaded "/usr/local/libexec/htslib/hfile_s3.so"
[D::init_add_plugin] Loaded "/usr/local/libexec/htslib/hfile_libcurl.so"
[D::init_add_plugin] Loaded "/usr/local/libexec/htslib/hfile_gcs.so"
*   Trying 147.75.201.93...
* TCP_NODELAY set
* Connected to play.min.io (147.75.201.93) port 9000 (#0)
* ALPN, offering http/1.1
* successfully set certificate verify locations:
*   CAfile: /etc/ssl/certs/ca-certificates.crt
  CApath: /etc/ssl/certs
* SSL connection using unknown / TLS_AES_128_GCM_SHA256
* ALPN, server accepted to use http/1.1
* Server certificate:
*  subject: CN=play.minio.io
*  start date: Jul  2 08:22:01 2019 GMT
*  expire date: Sep 30 08:22:01 2019 GMT
*  subjectAltName: host "play.min.io" matched cert's "play.min.io"
*  issuer: C=US; O=Let's Encrypt; CN=Let's Encrypt Authority X3
*  SSL certificate verify ok.
> GET /testfiles/NA18537.vcf.gz HTTP/1.1
Host: play.min.io:9000
User-Agent: htslib/1.9-258-ga428aa2 libcurl/7.58.0
Accept: */*
Authorization: AWS4-HMAC-SHA256 Credential=Q3AM3UQ867SPQQA43P2F/20190710/us-east-1/s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date,Signature=c4dcdc1b3d49a33b231151f760fb54f07606f0c0016c002847cd646d94d0c34b
x-amz-date: 20190710T204159Z
x-amz-content-sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

< HTTP/1.1 200 OK
< Accept-Ranges: bytes
< Content-Length: 3185107
< Content-Security-Policy: block-all-mixed-content
< Content-Type: application/octet-stream
< ETag: "c876ca31f911ade7751eb23b4827253c"
< Last-Modified: Thu, 04 Jul 2019 17:02:02 GMT
< Server: MinIO/DEVELOPMENT.2019-07-06T17-09-12Z
< Vary: Origin
< X-Amz-Bucket-Region: us-east-1
< X-Amz-Request-Id: 15B0266CE660B4AD
< X-Amz-Server-Side-Encryption: AES256
< X-Xss-Protection: 1; mode=block
< Date: Wed, 10 Jul 2019 20:41:59 GMT
< 
s3://default@play/testfiles/NA18537.vcf.gz:     VCF version 4.1 BGZF-compressed variant calling data
* stopped the pause stream!
* Closing connection 0
```

Pay close attention to the "Host:". If your host is not being read correctly, play around with the host_base in ./s3cfg file and the file path you pass in with the htsfile command

## 3) Rebuild PySAM from source
If you already have PySAM installed, you need to uninstall it. We want to rebuild PySAM from source to make it use our custom htslib instead of the release version.

To install PySAM from source, refer to this link: https://github.com/pysam-developers/pysam 

### Clone the repository:
```
git clone https://github.com/pysam-developers/pysam.git
```

Change your directory into root of PySAM. 

### Install cython
Since pysam depends on cython, it has to be installed beforehand:
```
pip install cython
```

### Export environment variables
```
export HTSLIB_LIBRARY_DIR=/usr/local/lib
export HTSLIB_INCLUDE_DIR=/usr/local/include
```

### Install PySAM
```
python3 setup.py install
```

## 4) Run PySAM

### Create ./s3cfg file in root directory addressed in step 2)

### create a s3test.py file
```
from pysam import VariantFile

s3_path = "s3://default@play/testfiles/NA18537.vcf.gz"
vcf_in = VariantFile(s3_path)
for rec in vcf_in.fetch():
    print(rec.pos)
```

In the terminal run:
```
python3 s3test.py
```

If it was successful, it should print out each position in the vcf file

## 5) Use PySAM in your project

# Conclusion
The official release of PySAM does not support signed s3 file paths. To make PySAM work with signed s3 buckets, we must rebuild PySAM from source and point it to the developer version of htslib. I hope these steps have helped you get PySAM and s3 buckets working with your project. 