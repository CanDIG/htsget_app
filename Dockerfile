#FROM continuumio/miniconda3:latest
#FROM continuumio/miniconda3:4.6.14-alpine
FROM python:3.6-alpine

LABEL Maintainer="CanDIG Project"

USER root

RUN apk update

RUN apk add \
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
	git

#USER anaconda

#RUN source /home/anaconda/.profile && \
	#conda update conda -y && \
	#conda env update -n base

#RUN apt-get update && apt-get install -y \
	#autoconf \
	#automake \
	#make \
	#gcc \
	#perl \
	#build-essential \
	#zlib1g-dev \
	#libbz2-dev \
	#liblzma-dev \
	#libcurl4-gnutls-dev \
	#libssl-dev

COPY . /app
#WORKDIR /app

WORKDIR /app/lib/htslib
RUN autoheader && autoconf && ./configure && make && make install

WORKDIR /app/lib/pysam
RUN pip install cython
RUN export HTSLIB_LIBRARY_DIR=/usr/local/lib && \
	export HTSLIB_INCLUDE_DIR=/usr/local/include && \
	python3 setup.py install

#RUN conda update -n base -c defaults conda
#RUN conda env update -n base -f /app/environment.yml
RUN python3 /app/setup.py install

# Run the model service server
WORKDIR /app
ENTRYPOINT ["python3", "/app/htsget_server/server.py"]
