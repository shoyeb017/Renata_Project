"""
config_app has no views of its own — all functionality is exercised via
config_app.loader, which is covered by shifts/tests.py
(ActivityConfigAutoRegistrationTests) since that's where it's consumed in
practice (ingestion, analytics, insights). No additional tests live here
to avoid duplicating that coverage.
"""
