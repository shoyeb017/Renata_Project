from django.contrib import admin
from .models import ActivityConfiguration, SystemConfiguration


@admin.register(ActivityConfiguration)
class ActivityConfigurationAdmin(admin.ModelAdmin):
    list_display = ("activity_name", "category", "productive_status", "display_color", "is_auto_registered")
    list_filter = ("category", "productive_status", "is_auto_registered")
    search_fields = ("activity_name",)


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ("configuration_name", "configuration_value", "updated_at")
    search_fields = ("configuration_name",)
