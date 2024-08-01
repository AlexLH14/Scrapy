from src.apps.cron.enumeration import CronNames
from src.apps.cron.models.cron_job import CronJobModel


class CronProvider:

    @staticmethod
    def is_cron_enabled(cron_name):
        # Primero se comprueba el flag de procesar o no los spiders
        cron = CronJobModel.objects.get(job=CronNames.FLAG_SPIDERS.value)
        if not cron.active:
            return False
        # Se comprueba el cron concreto
        cron = CronJobModel.objects.get(job=cron_name)
        if not cron.active:
            return False
        return True
