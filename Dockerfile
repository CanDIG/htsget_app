FROM python:alpine
LABEL Maintainer="CanDIG Project"

RUN apk update

RUN apk add make build-base musl-dev zlib-dev bzip2-dev xz-dev libcurl curl-dev yaml-dev

COPY . /app

WORKDIR /app

RUN python setup.py install

# Run the model service server
ENTRYPOINT ["python3", "./htsget_server/server.py"]
