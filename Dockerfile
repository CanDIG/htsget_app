ARG venv_python
ARG alpine_version
FROM python:${venv_python}-alpine${alpine_version}

LABEL Maintainer="CanDIG Project"

USER root

RUN apk update

RUN apk add --no-cache \
	autoconf \
	automake \
	make \
	gcc \
	perl \
	bash \
	build-base \
	musl-dev \
	zlib-dev \
	bzip2-dev \
	xz-dev \
	libcurl \
	curl \
	curl-dev \
	yaml-dev \
	libressl-dev \
	git \
	sqlite

COPY . /app/htsget_server

WORKDIR /app/htsget_server

# copy env vars into config.ini
ARG opa_secret
ARG opa_url
ARG candig_auth
ARG minio_url
ARG minio_access_key
ARG minio_secret_key
ARG minio_bucket_name
RUN sed -i s@\<CANDIG_OPA_SECRET\>@${opa_secret}@ config.ini \
    && sed -i s@\<OPA_URL\>@${opa_url}@ config.ini \
    && sed -i s@\<CANDIG_AUTHORIZATION\>@${candig_auth}@ \
    && sed -i s@\<MINIO_URL\>@${minio_url}@ \
    && sed -i s@\<MINIO_ACCESS_KEY\>@${minio_access_key}@ \
    && sed -i s@\<MINIO_SECRET_KEY\>@${minio_secret_key}@ \
    && sed -i s@\<MINIO_BUCKET_NAME\>@${minio_bucket_name}@ \
	config.ini

RUN python setup.py install && pip install --no-cache-dir -r requirements.txt

RUN sqlite3 data/files.db -init data/files.sql

ENTRYPOINT ["python3", "htsget_server/server.py"]
