import json
import base64
import hashlib
from datetime import datetime, timedelta
from django.conf import settings


def create_jwt_token(user_id, email):
    """Create simple JWT-like token (without jwt library dependency)"""
    import json
    import base64
    
    # Header
    header = {
        'alg': 'HS256',
        'typ': 'JWT'
    }
    
    # Payload
    payload = {
        'user_id': user_id,
        'email': email,
        'iat': int(datetime.utcnow().timestamp()),
        'exp': int((datetime.utcnow() + timedelta(hours=getattr(settings, 'JWT_EXPIRY_HOURS', 168))).timestamp())
    }
    
    # Encode header and payload
    header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=')
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=')
    
    # Create signature
    message = header_encoded + b'.' + payload_encoded
    signature = base64.urlsafe_b64encode(
        hashlib.sha256(message + settings.JWT_SECRET.encode()).digest()
    ).rstrip(b'=')
    
    token = (header_encoded + b'.' + payload_encoded + b'.' + signature).decode()
    return token


def verify_jwt_token(token):
    """Verify JWT-like token and extract payload"""
    # Demo Mode Bypass
    if token == 'demo-token':
        from django.contrib.auth.models import User
        user = User.objects.filter(is_active=True).first()
        user_id = user.id if user else 1
        return {
            'user_id': user_id,
            'email': 'demo@MarketFlow.com',
            'exp': int((datetime.utcnow() + timedelta(hours=24)).timestamp())
        }

    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_encoded, payload_encoded, signature = parts
        
        # Verify signature
        message = header_encoded.encode() + b'.' + payload_encoded.encode()
        expected_signature = base64.urlsafe_b64encode(
            hashlib.sha256(message + settings.JWT_SECRET.encode()).digest()
        ).rstrip(b'=').decode()
        
        if signature != expected_signature:
            return None
        
        # Decode payload
        payload_encoded_padded = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded_padded)
        payload = json.loads(payload_decoded)
        
        # Check expiration
        if payload.get('exp', 0) < int(datetime.utcnow().timestamp()):
            return None
        
        return payload
    except Exception:
        return None
