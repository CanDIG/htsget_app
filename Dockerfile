ARG venv_python
FROM python:${venv_python}

LABEL Maintainer="CanDIG Project"
LABEL "candigv2"="htsget_app"

USER root

RUN groupadd -r candig && useradd -r candig -g candig

RUN apt-get update && apt-get -y install \
	cron \
	libpcre3  \
	libpcre3-dev \
	sqlite3 \
	postgresql-client \
    postgresql

COPY requirements.txt /app/htsget_server/requirements.txt

RUN pip install --no-cache-dir -r /app/htsget_server/requirements.txt

COPY . /app/htsget_server

WORKDIR /app/htsget_server

RUN chown -R candig:candig /app/htsget_server

USER candig

RUN touch initial_setup

ENTRYPOINT ["bash", "entrypoint.sh"]
