from .base import *

env.read_env(str(ROOT_DIR.path('cirbox/settings/.envdev')))

from .production import *

DEBUG = True

CORS_ORIGIN_ALLOW_ALL = True
BACK_DNS = "http://localhost:8000"
PHP_SCRAPPER = "http://172.30.0.99/"   # Mismo que para PROD
CRAWLER_PHP_IP = '34.247.5.76'
