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
ARG minio_bucket_name
ARG vault_url

RUN touch initial_setup && pip install --no-cache-dir -r requirements.txt

RUN sqlite3 data/files.db -init data/files.sql

ENTRYPOINT ["bash", "entrypoint.sh"]
