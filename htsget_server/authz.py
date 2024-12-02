import json
from config import AUTHZ, TEST_KEY
from flask import Flask
import database
import authx.auth
from candigv2_logging.logging import CanDIGLogger


logger = CanDIGLogger(__file__)


app = Flask(__name__)


class AuthzRequest:
    headers = {}
    method = None
    path = None

    def __init__(self, headers, method, path):
        self.headers = headers
        self.method = method
        self.path = path


def is_testing(request):
    if "Authorization" in request.headers and request.headers["Authorization"] == f"Bearer {TEST_KEY}":
        logger.warning("TEST MODE, AUTHORIZATION IS DISABLED")
        return True


def is_authed(id_, request):
    if request is None:
        return 401
    if is_testing(request):
        return 200 # no auth
    if has_full_authz(request):
        return 200
    if "Authorization" in request.headers:
        obj = database.get_drs_object(id_)
        if obj is not None and 'program' in obj:
            if is_program_authorized(request, obj['program']):
                return 200
        else:
            return 404
    else:
        return 401
    return 403


def get_authorized_programs(request):
    req = AuthzRequest(request.headers, request.method, request.url.path)
    if has_full_authz(req):
        return map(lambda x: x['id'], database.list_programs())
    if is_testing(req):
        return ["test-htsget"]
    try:
        return authx.auth.get_opa_datasets(req)
    except Exception as e:
        logger.warning(f"Couldn't authorize programs: {type(e)} {str(e)}")
        return []


def is_program_authorized(request, program_id):
    req = AuthzRequest(request.headers, request.method, request.url.path)
    if is_testing(req):
        return True
    if has_full_authz(req):
        return True
    if not "Authorization" in request.headers:
        return False
    return authx.auth.is_action_allowed_for_program(authx.auth.get_auth_token(req), method=req.method, path=req.path, program=program_id)


def has_full_authz(request):
    """
    Is the user associated with the token a site admin? Alternately, is this request from query or ingest?
    """
    if is_testing(request):
        return True
    if request_is_from_ingest(request) or request_is_from_query(request):
        return True
    if "Authorization" in request.headers:
        try:
            return authx.auth.has_full_authz(AuthzRequest(request.headers, request.method, request.url.path))
        except Exception as e:
            logger.warning(f"Couldn't authorize for full access: {type(e)} {str(e)}")
            return False
    return False


def get_s3_url(s3_endpoint=None, bucket=None, object_id=None, access_key=None, secret_key=None, region=None, public=False):
    return authx.auth.get_s3_url(s3_endpoint=s3_endpoint, bucket=bucket, object_id=object_id, access_key=access_key, secret_key=secret_key, region=region, public=public)


def request_is_from_query(request):
    if "X-Service-Token" in request.headers:
        return authx.auth.verify_service_token(service="query", token=request.headers["X-Service-Token"])
    return False


def request_is_from_ingest(request):
    if "X-Service-Token" in request.headers:
        return authx.auth.verify_service_token(service="candig-ingest", token=request.headers["X-Service-Token"])
    return False
