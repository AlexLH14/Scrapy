import linecache
import sys

from rest_framework import status
from rest_framework.exceptions import APIException


class BaseAPIException(APIException):
    ...


class BadRequest(BaseAPIException):
    status_code = status.HTTP_400_BAD_REQUEST


class Forbidden(BaseAPIException):
    status_code = status.HTTP_403_FORBIDDEN


class NotFound(BaseAPIException):
    status_code = status.HTTP_404_NOT_FOUND


class Conflict(BaseAPIException):
    status_code = status.HTTP_409_CONFLICT


class UnsupportedMediaType(BaseAPIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


class ExpectationFailed(BaseAPIException):
    status_code = status.HTTP_417_EXPECTATION_FAILED


class TooManyRequests(BaseAPIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


class UnprocessableEntityException(BaseAPIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


def print_exception():
    excod_type, excod_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), excod_obj)
