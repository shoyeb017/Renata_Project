"""
shifts.filters
==============
Applies dynamic query-param filters to a ShiftRecord queryset:
  - date_from / date_to        (date range)
  - reason                     (one or more activity_reason values, comma-separated)
  - category                   (one or more ActivityConfiguration.category values)
  - min_duration / max_duration

No filter option here is hardcoded to a specific activity; reason/category
values are matched against whatever exists in the data/config tables.
"""
from .models import ShiftRecord


def apply_filters(request, queryset=None):
    qs = queryset if queryset is not None else ShiftRecord.objects.select_related("activity_config").all()
    params = request.query_params

    date_from = params.get("date_from")
    date_to = params.get("date_to")
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    reasons = params.get("reason")
    if reasons:
        reason_list = [r.strip() for r in reasons.split(",") if r.strip()]
        if reason_list:
            qs = qs.filter(activity_reason__in=reason_list)

    categories = params.get("category")
    if categories:
        category_list = [c.strip() for c in categories.split(",") if c.strip()]
        if category_list:
            qs = qs.filter(activity_config__category__in=category_list)

    min_duration = params.get("min_duration")
    max_duration = params.get("max_duration")
    if min_duration:
        qs = qs.filter(duration_hours__gte=float(min_duration))
    if max_duration:
        qs = qs.filter(duration_hours__lte=float(max_duration))

    return qs
