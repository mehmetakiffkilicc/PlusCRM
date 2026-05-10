"""
Base utilities and mixins for views
"""
from django.contrib.auth.models import User
from ..auth import verify_jwt_token
import logging

logger = logging.getLogger(__name__)


def get_user_from_request(request):
    """Extract and verify JWT token from request header"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]
    payload = verify_jwt_token(token)

    if not payload:
        return None

    try:
        user = User.objects.get(id=payload['user_id'])
        return user
    except User.DoesNotExist:
        return None


class TokenAuthMixin:
    """Mixin to authenticate requests using JWT token"""
    def get_user_from_token(self, request, required=True):
        user = get_user_from_request(request)
        if not user and required:
            raise Exception('Giriş bilgileri verilmedi.')
        return user

    def try_get_user(self, request):
        """Try to get user without raising exception"""
        try:
            return get_user_from_request(request)
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            logger.debug(f"Failed to get user from request: {e}")
            return None
