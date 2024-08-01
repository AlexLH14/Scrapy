import json
import requests

from src.apps.certificate_order.models.log import Log
from src.models import AccessPermission
from django.conf import settings


class PHPClient:
    URLS = {
        'pkcs11': 'scrapper/pkcs11/',
        'clavepin': 'scrapper/pin/',
    }

    @staticmethod
    def requests(method, url, data=None):
        try:
            headers = {'WEBTOKENPHP': AccessPermission.objects.get(key='WEBTOKENBACK_PHP').value,
                       'Content-Type': 'application/json',
                       'Accept': 'application/json'}

            _url = f'{settings.PHP_SCRAPPER}{url}'
            response = requests.request(method=method, url=_url, data=json.dumps(data),
                                        headers=headers, timeout=(1200, 1200))
            # response.raise_for_status()
            return response
        except Exception as err:
            msg = f'{settings.PHP_SCRAPPER} - {str(headers)} - {str(data)} - {str(err)}'
            Log.objects.create(context='cron_crawler', response=msg, error=str(err))
            raise err
