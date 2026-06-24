from django.core.management.base import BaseCommand
from config_app.data_loader import load_data


class Command(BaseCommand):
    help = "Load shift CSV data into database"

    def handle(self, *args, **options):
        load_data()
        self.stdout.write(
            self.style.SUCCESS("Shift data loaded successfully")
        )