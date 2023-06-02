import json
from config import AUTHZ, TEST_KEY
from flask import Flask
import database
import authx.auth


app = Flask(__name__)


def is_authed(id_, request):
    if request is None:
        return 401
    if request.headers.get("Authorization") == f"Bearer {TEST_KEY}":
        print("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        app.logger.warning("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        return 200 # no auth
    if "Authorization" in request.headers:
        authed_datasets = get_authorized_datasets(request)
        if id_:
            obj = database.get_drs_object(id_)
            if obj is not None and 'datasets' in obj:
                for dataset in obj["datasets"]:
                    if (dataset in authed_datasets) and (authx.auth.is_permissible(request)):
                        return 200
        else:
            if (authx.auth.is_permissible(request)): return 200
    else:
        return 401
    return 403


def is_testing(request):
    if request.headers.get("Authorization") == f"Bearer {TEST_KEY}":
        print("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        app.logger.warning("WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        return True


def get_authorized_datasets(request):
    try:
        return authx.auth.get_readable_datasets(request, opa_url=AUTHZ['CANDIG_OPA_URL'], admin_secret=AUTHZ['CANDIG_OPA_SECRET'])
    except Exception as e:
        print(f"Couldn't authorize datasets: {type(e)} {str(e)}")
        app.logger.warning(f"Couldn't authorize datasets: {type(e)} {str(e)}")
        return []

def get_s3_url(request, s3_endpoint=None, bucket=None, object_id=None, access_key=None, secret_key=None, region=None, public=False):
    return authx.auth.get_s3_url(request, s3_endpoint=s3_endpoint, bucket=bucket, object_id=object_id, access_key=access_key, secret_key=secret_key, region=region, public=public)
