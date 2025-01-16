from django.core.management.base import BaseCommand
from detection.models import FallLog

class Command(BaseCommand):
    help = "Clears all fall detection logs"

    def handle(self, *args, **kwargs):
        FallLog.objects.all().delete()
        self.stdout.write("Fall logs cleared successfully.")
