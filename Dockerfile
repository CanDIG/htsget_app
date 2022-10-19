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

COPY requirements.txt /app/htsget_server/requirements.txt

RUN pip install --no-cache-dir -r /app/htsget_server/requirements.txt

COPY . /app/htsget_server

WORKDIR /app/htsget_server

RUN touch initial_setup

ENTRYPOINT ["bash", "entrypoint.sh"]
