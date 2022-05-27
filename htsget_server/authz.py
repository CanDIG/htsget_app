import requests
import json
import os
from config import AUTHZ, TEST_KEY, CANDIG_OPA_SITE_ADMIN_KEY, VAULT_S3_TOKEN
from flask import Flask
import drs_operations
import re


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
        token = get_auth_token(request.headers)
        authed_datasets = get_opa_datasets(token, request.path, request.method)
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


def is_site_admin(request):
    """
    Is the user associated with the token a site admin?
    """
    if AUTHZ["CANDIG_AUTHORIZATION"] != "OPA":
        print("WARNING: AUTHORIZATION IS DISABLED")
        app.logger.warning("WARNING: AUTHORIZATION IS DISABLED")
        return True # no auth
    if request.headers.get("Test_Key") == TEST_KEY:
        print("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        app.logger.warning("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        return True # no auth
    if "Authorization" in request.headers:
        token = get_auth_token(request.headers)
        response = requests.post(
            AUTHZ['CANDIG_OPA_URL'] + "/v1/data/idp/" + CANDIG_OPA_SITE_ADMIN_KEY,
        headers={"Authorization": f"Bearer {AUTHZ['CANDIG_OPA_SECRET']}"},
            json={
                "input": {
                        "token": token
                    }
                }
            )
        response.raise_for_status()
        if 'result' in response.json():
            return True
    return False


def get_auth_token(headers):
    """
    Extracts token from request's header Authorization
    """
    token = headers['Authorization']
    if token is None:
        return ""
    return token.split()[1]


def get_opa_datasets(token, path, method):
    """
    Get allowed dataset result from OPA
    """
    body = {
        "input": {
            "token": token,
            "body": {
                "path": path,
                "method": method
            }
        }
    }
    response = requests.post(
        AUTHZ['CANDIG_OPA_URL'] + "/v1/data/permissions/datasets",
        headers={"Authorization": f"Bearer {AUTHZ['CANDIG_OPA_SECRET']}"},
        json=body
    )
    response.raise_for_status()
    allowed_datasets = response.json()["result"]
    return allowed_datasets
