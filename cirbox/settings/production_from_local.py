from .base import *

# Frase de seguridad de conexión a producción
clave = 'voy a conectar a PROD'
res = input(f'Vas a conectar a producción. Escribe "{clave}" para continuar\n\n')
if res != clave:
    raise Exception('Has intentado conectar a producción sin insertar la clave de paso correcta')

PRODUCTION_FROM_LOCAL = True

env.read_env(str(ROOT_DIR.path('cirbox/settings/.envprod')))
