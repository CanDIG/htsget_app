from config import AUTHZ, TEST_KEY
import authx.auth
from candigv2_logging.logging import CanDIGLogger


logger = CanDIGLogger(__file__)


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
            if hasattr(request, "url"):
                return authx.auth.is_site_admin(AuthzRequest(request.headers, request.method, request.url.path))
            else:
                return authx.auth.is_site_admin(AuthzRequest(request.headers, request.method, request.path))
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
