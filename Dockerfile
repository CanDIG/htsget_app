FROM python:alpine
LABEL Maintainer="CanDIG Project"

RUN apk update

COPY . /app

WORKDIR /app

RUN python setup.py install

# Run the model service server
ENTRYPOINT ["python3", "./htsget_server/server.py"]
