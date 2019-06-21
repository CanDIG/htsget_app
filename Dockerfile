FROM python:3
LABEL Maintainer "CanDIG Project"

COPY . /app
WORKDIR /app

RUN python setup.py install

EXPOSE 3000

# Run the model service server
ENTRYPOINT [ "htsget_app", "--port", "3000"]