"""
Custom decorators for API views
"""
import logging
from functools import wraps
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED
from django.contrib.auth.models import User
from .auth import verify_jwt_token

logger = logging.getLogger(__name__)


def require_user(view_func):
    """
    Decorator that extracts and validates user from JWT token.
    Replaces repeated user lookup code pattern.

    Usage:
        @require_user
        def get(self, request, user=None):
            # user is now available and validated
            ...
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            logger.warning(f"Missing or invalid Authorization header")
            return Response(
                {'error': 'Giriş bilgileri verilmedi. Lütfen giriş yapın.'},
                status=HTTP_401_UNAUTHORIZED
            )

        token = auth_header[7:]  # Remove 'Bearer ' prefix
        payload = verify_jwt_token(token)

        if not payload:
            logger.warning(f"Invalid or expired JWT token")
            return Response(
                {'error': 'Geçersiz veya süresi dolmuş oturum. Lütfen tekrar giriş yapın.'},
                status=HTTP_401_UNAUTHORIZED
            )

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            logger.warning(f"User {payload.get('user_id')} not found")
            return Response(
                {'error': 'Kullanıcı bulunamadı.'},
                status=HTTP_401_UNAUTHORIZED
            )

        # Inject user into kwargs
        kwargs['user'] = user
        return view_func(self, request, *args, **kwargs)

    return wrapper


def optional_user(view_func):
    """
    Decorator that tries to extract user from JWT token but doesn't fail if missing.
    Useful for endpoints that work with or without authentication.

    Usage:
        @optional_user
        def get(self, request, user=None):
            if user:
                # Authenticated request
            else:
                # Anonymous request
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = None
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            payload = verify_jwt_token(token)

            if payload:
                try:
                    user = User.objects.get(id=payload['user_id'])
                except User.DoesNotExist:
                    logger.debug(f"User {payload.get('user_id')} not found")

        kwargs['user'] = user
        return view_func(self, request, *args, **kwargs)

    return wrapper


def log_request(view_func):
    """
    Decorator that logs incoming requests with method, path, and user info.
    Useful for debugging and audit trails.
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user_id = 'anonymous'
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            payload = verify_jwt_token(token)
            if payload:
                user_id = payload.get('user_id', 'unknown')

        logger.info(f"{request.method} {request.path} - User: {user_id}")
        return view_func(self, request, *args, **kwargs)

    return wrapper
