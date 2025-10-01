from rest_framework import status
from rest_framework.exceptions import APIException

from core.constants import NOT_FOUND


class NotFound(APIException):
    """Переопределяет формат ответа для ошибки 404."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = NOT_FOUND
