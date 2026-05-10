"""
Authentication Views (Register and Login)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED
from rest_framework.permissions import AllowAny
from rest_framework.throttling import BaseThrottle, AnonRateThrottle
from django.core.cache import cache
from django.contrib.auth.models import User
from ..serializers import RegisterSerializer, LoginSerializer
from ..auth import create_jwt_token
import logging

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        return Response({
            'status': 'available',
            'methods': ['POST'],
            'message': 'Registration endpoint is active. Use POST to register.'
        })

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            try:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )
                logger.info(f"User created successfully: id={user.id}")
                return Response({
                    'message': 'Kullanıcı başarıyla oluşturuldu',
                    'user_id': user.id,
                    'email': user.email
                }, status=HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}", exc_info=True)
                return Response({'error': f"Kullanıcı oluşturulurken bir hata oluştu: {str(e)}"}, status=HTTP_400_BAD_REQUEST)

        logger.warning("Registration validation failed")
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class EmailBasedLoginThrottle(BaseThrottle):
    """IP yerine email bazlı throttle — Railway load balancer IP'leri değiştirdiği için.

    Pencere başına en fazla RATE başarısız denemeye izin verir. Başarılı girişler
    sayacı sıfırlar. Engelleme sırasında sayaç artmaz (double-penalti önlenir).
    """
    RATE = 5
    WINDOW = 60  # saniye

    def _key(self, request):
        email = request.data.get('email', '').lower().strip()
        return f'login_throttle:{email}' if email else None

    def allow_request(self, request, view):
        key = self._key(request)
        if not key:
            return True
        count = cache.get(key, 0)
        if count >= self.RATE:
            self._wait_time = self.WINDOW
            return False
        cache.set(key, count + 1, timeout=self.WINDOW)
        return True

    def record_success(self, request):
        """Başarılı girişte throttle sayacını sıfırla."""
        key = self._key(request)
        if key:
            cache.delete(key)

    def wait(self):
        return getattr(self, '_wait_time', self.WINDOW)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [EmailBasedLoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning("Login failed: user not found")
            return Response({'error': 'email veya şifre yanlış'}, status=HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            logger.warning(f"Login failed: incorrect password for {email}")
            return Response({'error': 'email veya şifre yanlış'}, status=HTTP_401_UNAUTHORIZED)

        # Başarılı giriş — throttle sayacını sıfırla
        for throttle in self.get_throttles():
            if isinstance(throttle, EmailBasedLoginThrottle):
                throttle.record_success(request)

        token = create_jwt_token(user.id, user.email)
        logger.info(f"Login successful: user_id={user.id}")
        return Response({
            'message': 'Giriş başarılı',
            'token': token,
            'user': {'id': user.id, 'email': user.email}
        }, status=HTTP_200_OK)


class ProfileView(APIView):
    """
    View for retrieving and updating the current user's profile.
    """
    # permission_classes is handled by JWT token in our custom middleware or similar
    # For now, we'll verify the token manually if needed, or assume it's done at middleware level.
    # Looking at urls.py, these views are simple APIViews.
    
    def get(self, request):
        token = request.headers.get('Authorization', '').split(' ')[1] if 'Authorization' in request.headers else None
        if not token:
            return Response({'error': 'Token bulunamadı'}, status=HTTP_401_UNAUTHORIZED)
            
        from ..auth import verify_jwt_token
        payload = verify_jwt_token(token)
        if not payload:
            return Response({'error': 'Geçersiz veya süresi dolmuş token'}, status=HTTP_401_UNAUTHORIZED)
            
        try:
            user = User.objects.get(id=payload['user_id'])
            return Response({
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined
            }, status=HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'Kullanıcı bulunamadı'}, status=HTTP_400_BAD_REQUEST)

    def post(self, request):
        token = request.headers.get('Authorization', '').split(' ')[1] if 'Authorization' in request.headers else None
        if not token:
            return Response({'error': 'Token bulunamadı'}, status=HTTP_401_UNAUTHORIZED)
            
        from ..auth import verify_jwt_token
        payload = verify_jwt_token(token)
        if not payload:
            return Response({'error': 'Geçersiz veya süresi dolmuş token'}, status=HTTP_401_UNAUTHORIZED)
            
        try:
            user = User.objects.get(id=payload['user_id'])
            data = request.data
            
            # Update password if provided
            new_password = data.get('password')
            if new_password:
                user.set_password(new_password)
                user.save()
                return Response({'message': 'Şifre başarıyla güncellendi'}, status=HTTP_200_OK)
            
            # Update other fields (optional, if we add more profile fields later)
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            if first_name is not None: user.first_name = first_name
            if last_name is not None: user.last_name = last_name
            user.save()
            
            return Response({'message': 'Profil güncellendi'}, status=HTTP_200_OK)
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            return Response({'error': str(e)}, status=HTTP_400_BAD_REQUEST)
