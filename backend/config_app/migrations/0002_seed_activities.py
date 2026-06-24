from django.db import migrations


def seed_activities(apps, schema_editor):
    ActivityConfiguration = apps.get_model(
        "config_app",
        "ActivityConfiguration"
    )

    activities = [
    ("Breakdown", False, "Failure", "#EF4444"),
    ("Machine Jam", False, "Failure", "#F97316"),
    ("Power Failure", False, "Failure", "#DC2626"),
    ("Unknown Failure", False, "Failure", "#B91C1C"),

    ("Cleaning", False, "Planned Downtime", "#8B5CF6"),
    ("Maintenance", False, "Planned Downtime", "#7C3AED"),

    ("Idle", False, "Idle", "#6B7280"),

    ("Material Shortage", False, "Logistics", "#F59E0B"),

    ("Other", False, "Uncategorized", "#94A3B8"),

    ("Quality Check", True, "Productive", "#14B8A6"),
    ("Setup", True, "Productive", "#3B82F6"),
    ("Training", True, "Productive", "#22C55E"),
    ]

    for name, productive, category, color in activities:
        ActivityConfiguration.objects.get_or_create(
            activity_name=name,
            defaults={
                "productive_status": productive,
                "category": category,
                "display_color": color,
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