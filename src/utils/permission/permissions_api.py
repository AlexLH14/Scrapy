import logging

from rest_framework.permissions import BasePermission
from ...models.permission import AccessPermission

logger = logging.getLogger(__name__)


class IsAuthenticatedAPI(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        web_token = request.META.get('HTTP_WEBTOKENCRAWLER', None)
        if not web_token:
            return False
        if AccessPermission.objects.filter(key='WEBTOKENCRAWLER', value=web_token).first():
            return True
        return False

    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return True
