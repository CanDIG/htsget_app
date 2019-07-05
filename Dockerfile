FROM continuumio/miniconda3:latest

LABEL Maintainer="CanDIG Project"

USER root

#RUN apk update

#RUN apk add make build-base musl-dev zlib-dev bzip2-dev xz-dev libcurl curl curl-dev yaml-dev

#USER anaconda

#RUN source /home/anaconda/.profile && \
	#conda update conda -y && \
	#conda env update -n base

COPY . /app
WORKDIR /app

#RUN conda update -n base -c defaults conda
RUN conda env update -n base

RUN python setup.py install

# Run the model service server
ENTRYPOINT ["python3", "/app/htsget_server/server.py"]
