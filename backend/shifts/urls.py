from django.urls import path
from . import views

urlpatterns = [
    path("dashboard-summary", views.dashboard_summary, name="dashboard-summary"),
    path("shift-analysis", views.shift_analysis, name="shift-analysis"),
    path("activity-distribution", views.activity_distribution, name="activity-distribution"),
    path("breakdown-trend", views.breakdown_trend, name="breakdown-trend"),
    path("failure-heatmap", views.failure_heatmap, name="failure-heatmap"),
    path("breakdown-streaks", views.breakdown_streaks, name="breakdown-streaks"),
    path("insights", views.insights, name="insights"),
    path("filter-options", views.filter_options, name="filter-options"),
]
