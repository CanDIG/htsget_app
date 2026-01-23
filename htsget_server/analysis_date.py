import htsget_operations
import database
import os
import sys
import hashlib
import re
import datetime
from candigv2_logging.logging import initialize, CanDIGLogger
import requests
from authx.auth import create_service_token
import json
from server import Session
from sqlalchemy import Column, Integer, String, JSON, Boolean, MetaData, Date, ForeignKey, Table, select


logger = CanDIGLogger(__file__)

initialize()


def find_analysis_dates():
    service_headers = {
        "X-Service-Token": create_service_token()
    }

    headers_by_vf = {}
    with Session() as session:
        q = select(database.VariantFile.id, database.Header.text)
        q = q.join(database.VariantFile, database.Header.associated_variantfiles)
        q = q.where(database.Header.text.contains("%ate=%")).order_by(database.VariantFile.id)
        for row in session.execute(q):
            result = row._mapping
            if result["id"] not in headers_by_vf:
                headers_by_vf[result["id"]] = []
            headers_by_vf[result["id"]].append(result["text"])

    result = {
        "date_added_to": [],
        "errors": []
    }
    for vf in headers_by_vf:
        analysis_date = database.get_analysis_date_from_headers(headers_by_vf[vf])
        if "datetime" in str(type(analysis_date)):
            analysis_date = analysis_date.strftime("%Y-%m-%d")
        response = write_analysis_date(vf, service_headers, analysis_date)
        if response.status_code == 200:
            result["date_added_to"].append({vf: analysis_date})
        else:
            result["errors"].append(f"{vf}: {response.status_code} {response.text}")

    return result

def write_analysis_date(drs_obj_id, headers, analysis_date):
    response = requests.get(url=f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/objects/{drs_obj_id}", headers=headers)
    if response.status_code == 200:
        obj = response.json()
        obj["metadata"]["analysis_date"] = analysis_date
        response = requests.post(url=f"{os.getenv("DRS_URL")}/ga4gh/drs/v1/objects", headers=headers, json=obj)
        return response
    return response


if __name__ == "__main__":
    print(json.dumps(find_analysis_dates(), indent=2))
