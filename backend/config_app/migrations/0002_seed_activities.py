from django.db import migrations


def seed_activities(apps, schema_editor):
    ActivityConfiguration = apps.get_model(
        "config_app",
        "ActivityConfiguration"
    )

    activities = [
        ("Breakdown", False, "Failure"),
        ("Machine Jam", False, "Failure"),
        ("Power Failure", False, "Failure"),
        ("Unknown Failure", False, "Failure"),

        ("Cleaning", False, "Planned Downtime"),
        ("Maintenance", False, "Planned Downtime"),

        ("Idle", False, "Idle"),

        ("Material Shortage", False, "Logistics"),

        ("Other", False, "Uncategorized"),

        ("Quality Check", True, "Productive"),
        ("Setup", True, "Productive"),
        ("Training", True, "Productive"),
    ]

    for name, productive, category in activities:
        ActivityConfiguration.objects.get_or_create(
            activity_name=name,
            defaults={
                "productive_status": productive,
                "category": category,
                "is_auto_registered": False,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("config_app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_activities),
    ]