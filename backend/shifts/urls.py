from django.urls import path
from . import views

urlpatterns = [
    path("dashboard-summary", views.dashboard_summary, name="dashboard-summary"),
    path("shift-analysis", views.shift_analysis, name="shift-analysis"),
    path("activity-distribution", views.activity_distribution, name="activity-distribution"),
    path("breakdown-trend", views.breakdown_trend, name="breakdown-trend"),
    path("breakdown-streaks", views.breakdown_streaks, name="breakdown-streaks"),
    path("data-quality-report", views.data_quality_report, name="data-quality-report"),
    path("insights", views.insights, name="insights"),
    path("filter-options", views.filter_options, name="filter-options"),
    path("datasets", views.list_datasets, name="list-datasets"),
    path("datasets/upload", views.upload_dataset, name="upload-dataset"),
    path("datasets/<int:dataset_id>/activate", views.activate_dataset, name="activate-dataset"),
]
