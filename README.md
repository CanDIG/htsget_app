# Htsget Application

Htsget API implementation that is based on the [Htsget retrieval API specifications](http://samtools.github.io/hts-specs/htsget.html)

## Stack
- [Connexion](https://github.com/zalando/connexion) for implementing the API
- [Sqlite3](https://www.sqlite.org/index.html)
- [ga4gh Data-Repostitory-Service(DRS)](https://github.com/ga4gh/data-repository-service-schemas)
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

# Running
The server can be run with 
```
python htsget_server/server.py
```
For testing, a small test suite under tests/test_htsget_server.py can be run by starting the server and running:
```
pytest tests/test_htsget_server.py
```
For automated testing, activate the repo with [Travis-CI](https://travis-ci.com/getting_started)