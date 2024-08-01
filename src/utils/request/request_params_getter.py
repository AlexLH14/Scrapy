import re

from rest_framework.exceptions import ParseError


class RequestParamsGetter:
    def __init__(self, request):
        self.request = request

    def get_param(self, param: str, default=False):
        try:
            return self.request.data[param]
        except Exception:
            if default is not False:
                return default
            raise ParseError(f'Parámetros {param} no en la búsqueda')

    @staticmethod
    def get_token(request):
        from rest_framework.authentication import get_authorization_header
        authorization_header = get_authorization_header(request).decode('utf-8')
        token = re.split('bearer ', authorization_header, flags=re.IGNORECASE)
        return token[1].strip()

    def get_file(self, param, required=False):
        try:
            return self.request.FILES[param].name, self.request.FILES[param]
        except Exception:
            if required:
                raise ParseError({f'{param}': 'Este campo es requerido'})
        return None
