from rest_framework.exceptions import APIException
from rest_framework import status

class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service temporarily unavailable.'
    default_code = 'service_unavailable'

class PlanetAPIError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'Error communicating with Planet API.'
    default_code = 'planet_api_error'

class ModelTrainingError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Error during model training.'
    default_code = 'model_training_error'

class PredictionError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Error generating prediction.'
    default_code = 'prediction_error'

class InvalidInputError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid input data.'
    default_code = 'invalid_input' 