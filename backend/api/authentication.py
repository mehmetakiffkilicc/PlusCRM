"""
JWT Authentication for Django REST Framework
"""
from rest_framework import authentication
from rest_framework import exceptions
from django.contrib.auth.models import User
from .auth import verify_jwt_token


class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT Authentication class for Django REST Framework.
    Expects Authorization header: Bearer <token>
    """

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        import logging
        logger = logging.getLogger('api')
        
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header:
            logger.debug("Authentication: No Authorization header provided.")
            return None

        # Parse Bearer token
        parts = auth_header.split()

        if len(parts) == 0:
            return None

        if parts[0].lower() != 'bearer':
            logger.debug(f"Authentication: Invalid prefix {parts[0]}")
            return None

        if len(parts) == 1:
            logger.warning("Authentication: Token string missing.")
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')

        if len(parts) > 2:
            logger.warning("Authentication: Token string contains spaces.")
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        token = parts[1]
        try:
            return self.authenticate_credentials(token)
        except exceptions.AuthenticationFailed as e:
            logger.error(f"Authentication Failed: {str(e)}")
            raise e

    def authenticate_credentials(self, token):
        """
        Verify the token and return the user.
        """
        import logging
        from django.contrib.auth.models import User
        logger = logging.getLogger('api')

        # Demo Mode Bypass
        if token == 'demo-token':
            logger.info("Authentication: Demo-token detected. Granting access to demo user.")
            user = User.objects.filter(is_active=True).first()
            if not user:
                # Create a demo user if none exists
                user, _ = User.objects.get_or_create(username='demo', email='demo@MarketFlow.com')
            return (user, token)

        payload = verify_jwt_token(token)

        if payload is None:
            logger.error("Authentication: verify_jwt_token returned None (possibly expired or invalid signature).")
            raise exceptions.AuthenticationFailed('Invalid or expired token.')

        try:
            user_id = payload.get('user_id')
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error(f"Authentication: User with ID {user_id} not found.")
            raise exceptions.AuthenticationFailed('User not found.')

        if not user.is_active:
            logger.error(f"Authentication: User {user.username} is inactive.")
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        return (user, token)

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'Bearer realm="api"'

