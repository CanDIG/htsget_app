import requests
import json
import configparser


config = configparser.ConfigParser()
config.read('./config.ini')


def get_opa_token_from_request(headers):
    """
    Extracts token from request's header Authorization
    """
    token = headers['Authorization']
    if token is None:
        return ""
    else:
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
    try:
        response = requests.post(
            config['authz']['CANDIG_OPA_URL'] + "/v1/data/permissions/datasets",
            headers={"Authorization": f"Bearer {config['authz']['CANDIG_OPA_SECRET']}"},
            json=get_request_body(headers, path, method)
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        error_response = {
            "error": "This request failed because we are unable to retrieve necessary info related to your account. Please contact your system administrator for assistance."
        }
        response = HttpResponseForbidden(json.dumps(error_response))
        response["Content-Type"] = "application/json"
        return ("error", response)
    allowed_datasets = response.json()["result"]
    return allowed_datasets


def is_site_admin(headers):
    try:
        response = requests.post(
            config['authz']['CANDIG_OPA_URL'] + "/v1/data/idp/trusted_researcher",
            headers={"Authorization": f"Bearer {config['authz']['CANDIG_OPA_SECRET']}"},
            json=get_request_body(headers, "", "")
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        error_response = {
            "error": "This request failed because we are unable to retrieve necessary info related to your account. Please contact your system administrator for assistance."
        }
        response = HttpResponseForbidden(json.dumps(error_response))
        response["Content-Type"] = "application/json"
        return ("error", response)
    if response.json()['result'] == 'true':
        return True
    return False
