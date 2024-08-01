import os

import requests
import json

from src.models import AccessPermission
from django.conf import settings


class BackClient:
    URLS = {
        'get_certificate': 'requests/crawler/get_certificate/',
        'send_document': 'requests/crawler/set_certificate_doc/',
        'send_status': 'requests/crawler/set_certificate_status/',
        'requests': 'requests/',
        'products': 'products/'
    }

    @staticmethod
    def requests(method, url, data=None, params=None):
        headers = {'WEBTOKENBACK': AccessPermission.objects.get(key='WEBTOKENBACK').value,
                   'Content-Type': 'application/json',
                   'authorization': f'Bearer {os.environ.get("ACCESS_TOKEN", default=None)}'}

        if data:
            data = json.dumps(data)

        url = f'{settings.BACK_DNS}/{url}'
        # url = f'https://api-dev.pinpass.es/{url}'
        # url = f'http://localhost:9009/{url}'
        # url = f'https://api.pinpass.es/{url}'

        response = requests.request(method=method, url=url, data=data, params=params, headers=headers)
        response.raise_for_status()
        return response
