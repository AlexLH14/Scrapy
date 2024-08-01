from enum import Enum


class ProductType(Enum):
    RENTA = 'renta'
    VIDA_LABORAL = 'vida_laboral'
    CIRBE = 'cirbe'
    IVA = 'iva'
    PENSIONES = 'pensiones'
    SOCIEDADES = 'sociedades'
    BASE_COTIZACION = 'base_cotizacion'
    MODELO_200 = 'modelo_200'
    MODELO_303 = 'modelo_303'
    MODELO_347 = 'modelo_347'
    MODELO_390 = 'modelo_390'

    @classmethod
    def values(cls):
        return tuple((i.value, i.name) for i in cls)

    @classmethod
    def values_list(cls):
        return list(i.value for i in cls)


class CertificateOrderType(Enum):
    COMPLETADO = 'COMPLETADO'
    ERROR = 'ERROR'
    PENDIENTE = 'PENDIENTE'
    PROCESANDO = 'PROCESANDO'
    NO_PROGRAMADO = 'NO_PROGRAMADO'
    STATUS_APPROVED = 'APPROVED'
    STATUS_STARTED = 'STARTED'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'

    @classmethod
    def values(cls):
        return tuple((i.value, i.name) for i in cls)


class CertificateOrderModeEnum(Enum):
    P12 = 'P12'
    PKCS11 = 'PKCS11'
    CLAVEPIN = 'CLAVEPIN'

    @classmethod
    def values(cls):
        return tuple((i.value, i.name) for i in cls)


class PersonType(Enum):
    J = 1
    F = 2

    @classmethod
    def values(cls):
        return tuple((i.value, i.name) for i in cls)

    @classmethod
    def values_list(cls):
        return list(i.value for i in cls)


