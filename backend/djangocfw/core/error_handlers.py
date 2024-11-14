from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from loguru import logger
import traceback

def custom_exception_handler(exc, context):
    """Custom exception handler for REST framework views."""
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Log the error
    logger.error(f"Exception in {context['view'].__class__.__name__}: {str(exc)}")
    logger.debug(f"Traceback: {''.join(traceback.format_tb(exc.__traceback__))}")

    # If response is already handled by DRF, add extra info
    if response is not None:
        response.data['status_code'] = response.status_code
        if hasattr(exc, 'get_full_details'):
            response.data['details'] = exc.get_full_details()
        return response

    # Handle Django's ValidationError
    if isinstance(exc, ValidationError):
        return Response({
            'status_code': 400,
            'error': 'Validation Error',
            'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
        }, status=400)

    # Handle database integrity errors
    if isinstance(exc, IntegrityError):
        return Response({
            'status_code': 400,
            'error': 'Database Error',
            'details': str(exc)
        }, status=400)

    # Handle any other exceptions
    logger.exception("Unhandled exception")
    return Response({
        'status_code': 500,
        'error': 'Internal Server Error',
        'details': str(exc) if str(exc) else 'An unexpected error occurred'
    }, status=500) 