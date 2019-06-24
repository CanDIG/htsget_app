FROM python:3
LABEL Maintainer "CanDIG Project"

COPY . /app
WORKDIR /app

RUN python setup.py install

# Run the model service server
CMD ["python3", "./htsget_server/server.py"]