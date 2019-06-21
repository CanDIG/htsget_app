FROM python:3
LABEL Maintainer "CanDIG Project"

COPY . /app
WORKDIR /app

RUN python setup.py install

EXPOSE 3000

# Run the model service server
# provide some explicit defaults if no arugments are given
ENTRYPOINT [ "htsget_app", "--port", "3000"]