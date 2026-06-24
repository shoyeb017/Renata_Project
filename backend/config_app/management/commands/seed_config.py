import json
from pathlib import Path
from django.core.management.base import BaseCommand
from config_app.models import ActivityConfiguration, SystemConfiguration

APP_DIR = Path(__file__).resolve().parent.parent.parent
ACTIVITY_CONFIG_PATH = APP_DIR / "data" / "activity_config.json"
SYSTEM_CONFIG_PATH = APP_DIR / "data" / "system_config.json"


class Command(BaseCommand):
    help = (
        "Seed ActivityConfiguration and SystemConfiguration tables from "
        "activity_config.json and system_config.json. Safe to re-run: "
        "existing rows are left untouched unless --force is passed, so "
        "manager edits made via the admin/API are never silently overwritten."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing rows with values from the JSON seed files.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        created_count = 0
        updated_count = 0

        with open(ACTIVITY_CONFIG_PATH) as f:
            activity_data = json.load(f)

        for entry in activity_data.get("activities", []):
            obj, created = ActivityConfiguration.objects.get_or_create(
                activity_name__iexact=entry["name"],
                defaults={
                    "activity_name": entry["name"],
                    "productive_status": entry.get("productive", False),
                    "category": entry.get("category", "Uncategorized"),
                    "display_color": entry.get("display_color", "#6E7681"),
                    "is_auto_registered": False,
                },
            )
            if created:
                created_count += 1
            elif force:
                obj.productive_status = entry.get("productive", obj.productive_status)
                obj.category = entry.get("category", obj.category)
                obj.display_color = entry.get("display_color", obj.display_color)
                obj.save()
                updated_count += 1

        with open(SYSTEM_CONFIG_PATH) as f:
            system_data = json.load(f)

        for entry in system_data.get("settings", []):
            obj, created = SystemConfiguration.objects.get_or_create(
                configuration_name=entry["configuration_name"],
                defaults={
                    "configuration_value": entry["configuration_value"],
                    "description": entry.get("description", ""),
                },
            )
            if created:
                created_count += 1
            elif force:
                obj.configuration_value = entry["configuration_value"]
                obj.description = entry.get("description", obj.description)
                obj.save()
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Config seed complete. Created: {created_count}, Updated: {updated_count}"
        ))
