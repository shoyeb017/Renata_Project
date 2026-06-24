from django.db import migrations


def seed_activities(apps, schema_editor):
    ActivityConfiguration = apps.get_model(
        "config_app",
        "ActivityConfiguration"
    )

    activities = [
        # Failure
        ("Breakdown", False, "Failure", "#EF4444"),
        ("Machine Jam", False, "Failure", "#DC2626"),
        ("Power Failure", False, "Failure", "#B91C1C"),
        ("Unknown Failure", False, "Failure", "#F87171"),

        # Planned Downtime
        ("Cleaning", False, "Planned Downtime", "#F59E0B"),
        ("Maintenance", False, "Planned Downtime", "#D97706"),

        # Idle
        ("Idle", False, "Idle", "#6B7280"),

        # Logistics
        ("Material Shortage", False, "Logistics", "#8B5CF6"),

        # Uncategorized
        ("Other", False, "Uncategorized", "#94A3B8"),

        # Productive
        ("Quality Check", True, "Productive", "#10B981"),
        ("Setup", True, "Productive", "#059669"),
        ("Training", True, "Productive", "#34D399"),
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