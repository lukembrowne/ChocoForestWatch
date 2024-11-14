import logging
import json
from django.utils.timezone import now
from loguru import logger
import sys

# Configure loguru logger
logger.remove()  # Remove default handler
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)
logger.add(sys.stderr, level="INFO")

class RequestResponseLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request
        request_time = now()
        method = request.method
        path = request.path
        query_params = dict(request.GET)

        logger.info(f"Request: {method} {path}")
        logger.debug(f"Query params: {query_params}")
        
        if method in ['POST', 'PUT', 'PATCH']:
            try:
                body = json.loads(request.body) if request.body else {}
                logger.debug(f"Request body: {body}")
            except json.JSONDecodeError:
                logger.debug("Request body: <non-JSON data>")

        # Get response
        response = self.get_response(request)

        # Log response
        status_code = response.status_code
        duration = (now() - request_time).total_seconds()
        
        logger.info(f"Response: {status_code} (took {duration:.2f}s)")
        if status_code >= 400:
            try:
                response_data = json.loads(response.content)
                logger.error(f"Error response: {response_data}")
            except json.JSONDecodeError:
                logger.error(f"Error response: {response.content}")

        return response

    def process_exception(self, request, exception):
        logger.exception(f"Unhandled exception in {request.method} {request.path}: {str(exception)}")
        return None

class APIErrorLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.exception(f"API Error: {str(exception)}")
        return None 