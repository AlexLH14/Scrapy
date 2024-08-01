from .base import *

# from .production_from_local import *
# env.read_env(str(ROOT_DIR.path('cirbox/settings/.envlocal')))
env.read_env(str(ROOT_DIR.path('cirbox/settings/.envprod')))
from .production import *

DEBUG = True

CORS_ORIGIN_ALLOW_ALL = True
BACK_DNS = 'http://localhost:8010'
PHP_SCRAPPER = "http://18.200.229.88/"
CRAWLER_PHP_IP = '34.247.5.76'
