from django.core.management.base import BaseCommand
from core.utils import perform_sync

class Command(BaseCommand):
    help = 'Sync market ticker and instrument LTP data from Google Sheets'

    def handle(self, *args, **options):
        self.stdout.write("Starting sync process...")
        try:
            perform_sync()
            self.stdout.write(self.style.SUCCESS("Sync process completed."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Sync process failed: {e}"))
