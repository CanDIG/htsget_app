ARG venv_python
ARG alpine_version
FROM python:${venv_python}-alpine${alpine_version}

LABEL Maintainer="CanDIG Project"
LABEL "candigv2"="htsget_app"

USER root

RUN addgroup -S candig && adduser -S candig -G candig

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
	linux-headers \
	curl \
	curl-dev \
	yaml-dev \
	libressl-dev \
	pcre-dev \
	git \
	sqlite

COPY requirements.txt /app/htsget_server/requirements.txt

RUN pip install --no-cache-dir -r /app/htsget_server/requirements.txt

COPY . /app/htsget_server

WORKDIR /app/htsget_server

RUN touch initial_setup

ENTRYPOINT ["bash", "entrypoint.sh"]
