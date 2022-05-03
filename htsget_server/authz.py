import requests
import json
import os
from config import AUTHZ, TEST_KEY
from flask import Flask
import drs_operations


app = Flask(__name__)


def is_authed(id_, request):
    if AUTHZ["CANDIG_AUTHORIZATION"] != "OPA":
        print("WARNING: AUTHORIZATION IS DISABLED")
        app.logger.warning("WARNING: AUTHORIZATION IS DISABLED")
        return 200 # no auth
    if request.headers.get("Test_Key") == TEST_KEY:
        print("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        app.logger.warning("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        return 200 # no auth
    if "Authorization" in request.headers:
        authed_datasets = get_opa_res(request.headers, request.path, request.method)
        obj, code2 = drs_operations.get_object(id_)
        if code2 == 200:
            for dataset in obj["datasets"]:
                if dataset in authed_datasets:
                    return 200
        else:
            msg = json.dumps(obj, indent=4)
            print(msg)
            app.logger.warning(msg)
            return code2
    else:
        return 401
    return 403


def get_opa_token_from_request(headers):
    """
    Extracts token from request's header Authorization
    """
    token = headers['Authorization']
    if token is None:
        return ""
    return token.split()[1]


def get_request_body(headers, path, method):
    """
    Returns request body required to query OPA
    """
    return {
        "input": {
            "token": get_opa_token_from_request(headers),
            "body": {
                "path": path,
                "method": method
            }
        }
    }


def get_opa_res(headers, path, method):
    """
    Get allowed dataset result from OPA
    """
    response = requests.post(
        AUTHZ['CANDIG_OPA_URL'] + "/v1/data/permissions/datasets",
        headers={"Authorization": f"Bearer {AUTHZ['CANDIG_OPA_SECRET']}"},
        json=get_request_body(headers, path, method)
    )
    response.raise_for_status()
    allowed_datasets = response.json()["result"]
    return allowed_datasets


def is_site_admin(headers):
    response = requests.post(
        AUTHZ['CANDIG_OPA_URL'] + "/v1/data/idp/trusted_researcher",
        headers={"Authorization": f"Bearer {AUTHZ['CANDIG_OPA_SECRET']}"},
        json=get_request_body(headers, "", "")
    )
    response.raise_for_status()
    if response.json()['result'] == 'true':
        return True
    return False
