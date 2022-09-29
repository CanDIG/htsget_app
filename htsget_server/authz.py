import json
from config import AUTHZ, TEST_KEY, VAULT_S3_TOKEN
from flask import Flask
import drs_operations
import authx.auth


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
        authed_datasets = get_authorized_datasets(request)
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


def get_authorized_datasets(request):
    return authx.auth.get_opa_datasets(request, AUTHZ['CANDIG_OPA_URL'], AUTHZ['CANDIG_OPA_SECRET'])


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
        return authx.auth.is_site_admin(request, AUTHZ['CANDIG_OPA_URL'], AUTHZ['CANDIG_OPA_SECRET'])
    return False



def get_aws_credential(request, endpoint, bucket):
    return authx.auth.get_aws_credential(request, endpoint, bucket, VAULT_S3_TOKEN)