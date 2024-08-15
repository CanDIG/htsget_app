import json
from config import AUTHZ, TEST_KEY
from flask import Flask
import database
import authx.auth
from candigv2_logging.logging import CanDIGLogger


logger = CanDIGLogger(__file__)


app = Flask(__name__)


def is_testing(request):
    if request.headers.get("Authorization") == f"Bearer {TEST_KEY}":
        logger.log_message("WARNING","WARNING: TEST MODE, AUTHORIZATION IS DISABLED")
        return True


def is_authed(id_, request):
    if request is None:
        return 401
    if is_testing(request):
        return 200 # no auth
    if "Authorization" in request.headers:
        obj = database.get_drs_object(id_)
        if obj is not None and 'cohort' in obj:
            if is_cohort_authorized(request, obj['cohort']) \
                or request_is_from_query(request):
                return 200
        else:
            return 404
    else:
        return 401
    return 403


def get_authorized_cohorts(request):
    if is_testing(request):
        return []
    try:
        return authx.auth.get_opa_datasets(request)
    except Exception as e:
        logger.log_message("WARNING",f"Couldn't authorize cohorts: {type(e)} {str(e)}")
        return []


def is_cohort_authorized(request, cohort_id):
    if is_testing(request):
        return True
    return authx.auth.is_action_allowed_for_program(authx.auth.get_auth_token(request), method=request.method, path=request.path, program=cohort_id)


def is_site_admin(request):
    """
    Is the user associated with the token a site admin?
    """
    if is_testing(request):
        return True
    if "Authorization" in request.headers:
        try:
            return authx.auth.is_site_admin(request)
        except Exception as e:
            logger.log_message("WARNING",f"Couldn't authorize site_admin: {type(e)} {str(e)}")
            return False
    return False


def get_s3_url(s3_endpoint=None, bucket=None, object_id=None, access_key=None, secret_key=None, region=None, public=False):
    return authx.auth.get_s3_url(s3_endpoint=s3_endpoint, bucket=bucket, object_id=object_id, access_key=access_key, secret_key=secret_key, region=region, public=public)


def request_is_from_query(request):
    if "X-Service-Token" in request.headers:
        return authx.auth.verify_service_token(service="query", token=request.headers["X-Service-Token"])
    return False
