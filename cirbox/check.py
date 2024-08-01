from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class HealthView(ViewSet):

    permission_classes = ()

    def list(self, request):
        return Response({
            'message': 'Still alive!'
        })
