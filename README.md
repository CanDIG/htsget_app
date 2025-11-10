# Htsget Application

Htsget API implementation that is based on the [Htsget retrieval API specifications](http://samtools.github.io/hts-specs/htsget.html).

Access to the underlying data objects is mediated through a "baby DRS" server which runs as a separate REST API. The [OpenAPI file](htsget_server/drs_openapi.yml) specifies a suggested format for DRS-compliant genomic variant, read, and index objects. Hopefully a compatible, separate DRS server will be able to implement this API as-is.


Thank you to [gel-htsget](https://github.com/genomicsengland/gel-htsget) for being a good starting point to this project

[![Build Status](https://travis-ci.org/CanDIG/htsget_app.svg?branch=master)](https://travis-ci.org/CanDIG/htsget_app)
[![CodeFactor](https://www.codefactor.io/repository/github/CanDIG/htsget_app/badge)](https://www.codefactor.io/repository/github/CanDIG/htsget_app)
[![PyUp](https://pyup.io/repos/github/CanDIG/htsget_app/shield.svg)](https://pyup.io/repos/github/CanDIG/htsget_app/)

## Stack
- [Connexion](https://github.com/zalando/connexion) for implementing the API
- [PostgreSQL](https://www.postgresql.org/)
- [ga4gh Data-Repository-Service(DRS)](https://github.com/ga4gh/data-repository-service-schemas)
- [minio-py](https://github.com/minio/minio-py)
- [Flask](http://flask.pocoo.org/)
- Python 3
- [Pysam](https://pysam.readthedocs.io/en/latest/api.html)
- Pytest

## Installation

The server is meant to be run in the context of the [CanDIG stack](https://candig.github.io/CanDIGv2/deployment/local/).

The default MinIO location specified in the config.ini file is the sandbox at MinIO, but a different location can be specified there as well. Be sure to update the access key and secret key values in config.ini.


## Testing

An automated test suite is provided, but can only be run in the docker container stack context. If you are running the CanDIG stack, you can run the tests with
```
docker exec candigv2_htsget_1 pytest
```
