"""
Utility functions for API views
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from django.contrib.auth.models import User
from .auth import verify_jwt_token

logger = logging.getLogger(__name__)


def get_user_from_request(request) -> Optional[User]:
    """
    Extract and verify JWT token from request header.
    Returns User object if valid, None otherwise.

    Args:
        request: Django request object

    Returns:
        User object or None
    """
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
        logger.warning(f"User {payload.get('user_id')} not found in get_user_from_request")
        return None


def parse_pagination_params(request, default_page_size: int = 50) -> Dict[str, Any]:
    """
    Extract pagination parameters from request query params.

    Args:
        request: Django request object
        default_page_size: Default page size if not specified

    Returns:
        Dictionary with pagination parameters
    """
    return {
        'page': int(request.query_params.get('page', 1)),
        'page_size': int(request.query_params.get('pageSize', request.query_params.get('page_size', default_page_size))),
        'search': request.query_params.get('search', request.query_params.get('q')),
        'sort_by': request.query_params.get('sortBy', request.query_params.get('sort_by')),
        'sort_dir': request.query_params.get('sortDir', request.query_params.get('sort_dir', 'ASC')),
    }


def parse_filter_params(request) -> Dict[str, Any]:
    """
    Extract filter parameters from request query params.
    Common filters: start_date, end_date, category, status, etc.

    Args:
        request: Django request object

    Returns:
        Dictionary with filter parameters
    """
    filters = {}

    # Date filters
    if 'start_date' in request.query_params or 'startDate' in request.query_params:
        filters['start_date'] = request.query_params.get('start_date', request.query_params.get('startDate'))

    if 'end_date' in request.query_params or 'endDate' in request.query_params:
        filters['end_date'] = request.query_params.get('end_date', request.query_params.get('endDate'))

    # Category filter
    if 'category' in request.query_params:
        filters['category'] = request.query_params.get('category')

    # Status filter
    if 'status' in request.query_params:
        filters['status'] = request.query_params.get('status')

    # Year/Month filters
    if 'year' in request.query_params:
        try:
            filters['year'] = int(request.query_params.get('year'))
        except (ValueError, TypeError) as e:
            logger.debug(f"Invalid year parameter: {e}")

    if 'month' in request.query_params:
        try:
            filters['month'] = int(request.query_params.get('month'))
        except (ValueError, TypeError) as e:
            logger.debug(f"Invalid month parameter: {e}")

    return filters


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float with fallback.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to convert to float: {value} - {e}")
        return default


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int with fallback.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Int value or default
    """
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to convert to int: {value} - {e}")
        return default


def safe_date_parse(date_str: str, format: str = '%Y-%m-%d') -> Optional[datetime]:
    """
    Safely parse date string to datetime object.

    Args:
        date_str: Date string to parse
        format: Date format string

    Returns:
        datetime object or None
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, format)
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Failed to parse date '{date_str}': {e}")
        return None


def format_error_response(error: Exception, default_message: str = "Bir hata oluştu") -> Dict[str, str]:
    """
    Format exception into standard error response.

    Args:
        error: Exception object
        default_message: Default error message

    Returns:
        Dictionary with error message
    """
    error_message = str(error) if str(error) else default_message
    logger.error(f"Error response: {error_message}", exc_info=True)

    return {
        'error': error_message,
        'type': type(error).__name__
    }


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> Optional[str]:
    """
    Validate that required fields are present in data dictionary.

    Args:
        data: Data dictionary to validate
        required_fields: List of required field names

    Returns:
        Error message if validation fails, None if valid
    """
    missing_fields = [field for field in required_fields if field not in data or not data[field]]

    if missing_fields:
        return f"Eksik alanlar: {', '.join(missing_fields)}"

    return None
