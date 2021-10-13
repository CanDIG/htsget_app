# Htsget Application

Htsget API implementation that is based on the [Htsget retrieval API specifications](http://samtools.github.io/hts-specs/htsget.html).

Access to the underlying data objects is mediated through a "baby DRS" server which runs as a separate REST API. The [OpenAPI file](htsget_server/drs_openapi.yml) specifies a suggested format for DRS-compliant genomic variant, read, and index objects. Hopefully a compatible, separate DRS server will be able to implement this API as-is.


Thank you to [gel-htsget](https://github.com/genomicsengland/gel-htsget) for being a good starting point to this project

[![Build Status](https://travis-ci.org/CanDIG/htsget_app.svg?branch=master)](https://travis-ci.org/CanDIG/htsget_app)
[![CodeFactor](https://www.codefactor.io/repository/github/CanDIG/htsget_app/badge)](https://www.codefactor.io/repository/github/CanDIG/htsget_app)
[![PyUp](https://pyup.io/repos/github/CanDIG/htsget_app/shield.svg)](https://pyup.io/repos/github/CanDIG/htsget_app/)

## Stack
- [Connexion](https://github.com/zalando/connexion) for implementing the API
- [Sqlite3](https://www.sqlite.org/index.html)
- [ga4gh Data-Repository-Service(DRS)](https://github.com/ga4gh/data-repository-service-schemas)
- [minio-py](https://github.com/minio/minio-py)
- [Flask](http://flask.pocoo.org/)
- Python 3
- [Pysam](https://pysam.readthedocs.io/en/latest/api.html)
- Pytest
- Travis-CI

## Installation

The server software can be installed in a virtual environment:
```
python setup.py install
```

## Running

This application can be configured by way of the config.ini file in the root of the project.
The server can be run with: 

```
python htsget_server/server.py
```

This application can also be set up in a docker container. A docker-compose file and Dockerfile are provided.

The default MinIO location specified in the config.ini file is the sandbox at MinIO, but a different location can be specified there as well. Be sure to update the access key and secret key values in config.ini.


## Testing

For testing, a small test suite under tests/test_htsget_server.py can be run by starting the server and running:

```
pytest
```

For automated testing, activate the repo with [Travis-CI](https://travis-ci.com/getting_started)
