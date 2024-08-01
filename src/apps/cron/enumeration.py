from enum import Enum


class CronNames(Enum):
    PROCESAR_PENDIENTES = 'PROCESAR_PENDIENTES'
    PROCESAR_ERROR = 'PROCESAR_ERROR'
    PROCESAR_PROCESANDO = 'PROCESAR_PROCESANDO'
    FLAG_SPIDERS = 'FLAG_SPIDERS'

    @classmethod
    def values(cls):
        return tuple((i.value, i.name) for i in cls)
