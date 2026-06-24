# Employee Shift Operational Analytics Dashboard

A full-stack web application that turns raw, messy employee shift logs into an operational picture a plant manager can act on: data quality auditing, operational efficiency scoring, breakdown streak detection, activity breakdowns, and auto-generated insights with recommended actions — all driven by configuration rather than hardcoded business rules, and all runnable against any CSV a user uploads at runtime.

This document is written as a self-contained manual: read it top to bottom and you will understand exactly what was built, why each design decision was made, and how to run, test, and extend the project.

---

## Table of Contents

1.  [Project Summary](#1-project-summary)
2.  [Features](#2-features)
3.  [Technology Stack](#3-technology-stack)
4.  [Project Structure](#4-project-structure)
5.  [The Data Pipeline](#5-the-data-pipeline)
6.  [Installation & Setup](#6-installation--setup)
    - [6.1 Prerequisites](#61-prerequisites)
    - [6.2 Backend Setup](#62-backend-setup)
    - [6.3 Frontend Setup](#63-frontend-setup)
    - [6.4 Running the App](#64-running-the-app)
7.  [API Reference](#7-api-reference)
    - [7.1 Filter-Aware Endpoints](#71-filter-aware-endpoints)
    - [7.2 Whole-Dataset Endpoints](#72-whole-dataset-endpoints)
    - [7.3 Dataset Management Endpoints](#73-dataset-management-endpoints)
    - [7.4 Filter Query Parameters](#74-filter-query-parameters)
8.  [Key Design Decisions](#8-key-design-decisions)
    - [8.1 No Hardcoding — The Configuration System](#81-no-hardcoding--the-configuration-system)
    - [8.2 Data Quality & Cleaning Assumptions](#82-data-quality--cleaning-assumptions)
    - [8.3 Dynamic Dataset Upload](#83-dynamic-dataset-upload)
    - [8.4 Why Breakdown Streaks & Data Quality Ignore Filters](#84-why-breakdown-streaks--data-quality-ignore-filters)
    - [8.5 Breakdown Streak Detection Algorithm](#85-breakdown-streak-detection-algorithm)
    - [8.6 Operational Insights Are Computed, Not Written](#86-operational-insights-are-computed-not-written)
    - [8.7 Visual Design Direction](#87-visual-design-direction)
9.  [Usage Guide](#9-usage-guide)
    - [9.1 Exploring the Default Dataset](#91-exploring-the-default-dataset)
    - [9.2 Uploading Your Own Dataset](#92-uploading-your-own-dataset)
    - [9.3 Filtering & Drilling In](#93-filtering--drilling-in)
    - [9.4 Reading the Breakdown Streaks Panel](#94-reading-the-breakdown-streaks-panel)
    - [9.5 Reading the Data Quality Report](#95-reading-the-data-quality-report)
    - [9.6 Reading Operational Insights](#96-reading-operational-insights)
    - [9.7 Reconfiguring Activities & Thresholds](#97-reconfiguring-activities--thresholds)
10. [Testing](#10-testing)
11. [Troubleshooting](#11-troubleshooting)
12. [Known Limitations & Next Steps](#12-known-limitations--next-steps)

---

## 1. Project Summary

A plant operates in shifts. Every shift, equipment runs, breaks down, gets maintained, or sits idle — and every one of those events gets logged as a row in a spreadsheet: a date, a start time, an end time, a duration, and a reason. Individually those rows are just data entry. Collectively, they answer the questions a manager actually has:

- _How efficient were we this period?_
- _Are breakdowns clustering around a specific time, or are they random?_
- _Is the source data itself trustworthy, or full of gaps and errors?_
- _What should I actually do about it?_

This project ingests that raw log, cleans it, classifies it against a configurable rulebook (not a hardcoded one), computes the analytics, and presents it through a REST API and a React dashboard — with the ability to swap in a completely different dataset at runtime via upload, with no code changes and no redeployment.

---

## 2. Features

- **Dynamic dataset upload** — load the bundled sample dataset by default, or upload any compatible CSV through the dashboard. Every dataset ever ingested is kept, so you can switch back and forth without re-uploading.
- **Automated data cleaning** — missing values, malformed dates, invalid timestamps, overnight shifts, duration mismatches, and duplicate rows are all detected and repaired (or rejected with a reason), never silently dropped without a trace.
- **Configurable activity classification** — every activity ("Breakdown", "Training", etc.) is mapped to a productivity flag, a category, and a color through a database table, not application code. Unknown activities in a new dataset are auto-registered rather than crashing the pipeline or being discarded.
- **Operational Efficiency Score** — productive hours divided by total hours, always computed live from whatever data and filters are active.
- **Interactive Shift Analysis timeline** — a Gantt-style chart (not a bar chart) showing every shift block across a 0-36 hour axis so overnight shifts render as one continuous block.
- **Activity Distribution & Breakdown Trend charts** — where the hours actually went, and how failure time moves over the date range.
- **Breakdown Streaks (whole-dataset view)** — detects clusters of failure events that occur close together in time, classifies their severity, and visualizes exactly where in the timeline they happened — deliberately independent of whatever filters are active elsewhere.
- **Data Quality Report (whole-dataset view)** — validity percentage, record counts, and an anomaly breakdown (zero-hour records, negative-hour records, statistical outliers, duplicates) for the dataset as it was ingested.
- **Operational Insights with recommended actions** — every insight card is generated from the live numbers (not pre-written text), each with a severity rating and a concrete suggested action.
- **Dynamic, combinable filters** — date range, activity reason, category, and duration range, all derived from whatever is actually in the data.

---

## 3. Technology Stack

| Layer              | Technology                                                                 |
| ------------------ | -------------------------------------------------------------------------- |
| Backend framework  | Django 5 + Django REST Framework                                           |
| Data processing    | Pandas, NumPy                                                              |
| Database           | SQLite by default; PostgreSQL via one environment variable                 |
| Frontend framework | React 19 + Vite                                                            |
| Charting           | Recharts (pie/area charts) + hand-built SVG (Gantt timeline, streak chart) |
| Frontend testing   | Vitest + React Testing Library                                             |
| Backend testing    | Django's built-in TestCase + DRF's APIClient                               |

---

## 4. Project Structure

```
shift-analytics/
├── README.md                     This file
├── backend/
│   ├── shift_analytics/          Django project (settings, root urls)
│   ├── config_app/               Configuration tables - the "rulebook"
│   │   ├── data/                   activity_config.json, system_config.json (seed files)
│   │   ├── models.py                ActivityConfiguration, SystemConfiguration
│   │   ├── loader.py                SINGLE access point for all config reads
│   │   └── management/commands/seed_config.py
│   ├── shifts/                   Core application logic
│   │   ├── models.py                Dataset, ShiftRecord, DataQualityReport
│   │   ├── cleaning.py              Data Quality Module (validation + repair)
│   │   ├── ingestion.py             Shared ingestion service (CLI + upload API)
│   │   ├── analytics.py             Analytics Engine (all computed metrics)
│   │   ├── insights.py              Insight generator (titles/metrics/actions/severity)
│   │   ├── filters.py               Dynamic query-param filter system
│   │   ├── views.py / urls.py       REST API
│   │   ├── tests.py                 Backend test suite
│   │   └── management/commands/ingest_shifts.py
│   ├── data/shift_data.csv       Bundled default dataset
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/client.js              REST client - every API call goes through here
    │   ├── hooks/useDashboardData.js  Central data + filter + dataset state
    │   ├── components/
    │   │   ├── DatasetPanel.jsx          Upload / switch dataset
    │   │   ├── FilterPanel.jsx           Dynamic filter controls
    │   │   ├── KpiCards.jsx              Efficiency score + summary KPIs
    │   │   ├── ShiftAnalysisChart.jsx    Custom Gantt-style timeline
    │   │   ├── ActivityLegend.jsx        Auto-updating activity/category legend
    │   │   ├── ActivityDistributionChart.jsx
    │   │   ├── BreakdownTrendChart.jsx
    │   │   ├── BreakdownStreaksPanel.jsx Whole-dataset streak visual + detail cards
    │   │   ├── DataQualityReportPanel.jsx Whole-dataset quality report
    │   │   └── InsightPanel.jsx          Insight cards (title/metric/action/severity)
    │   ├── pages/Dashboard.jsx        Composes everything above
    │   ├── styles/tokens.css          Design tokens (see Section 8.7)
    │   └── test/                      Vitest + RTL specs, one file per component
    └── package.json
```

---

## 5. The Data Pipeline

Every dataset — whether the bundled default or something you upload — flows through the exact same pipeline:

```
Raw CSV
   |
   v
Ingestion          (read into a DataFrame)
   |
   v
Validation &       (missing values, malformed dates/timestamps, duration
Cleaning            mismatches, overnight shifts, duplicates, anomaly counts)
   |
   v
Configuration       (each REASON resolved against ActivityConfiguration;
Rules                unknown activities auto-registered, never dropped)
   |
   v
Persistence         (stored as a new Dataset + its ShiftRecords; becomes
                     the active dataset; previous datasets are kept)
   |
   v
Analytics Engine    (efficiency, distribution, trend, streaks, quality report)
   |
   v
REST API  ------->  React Dashboard  ------->  Operational Insights
```

The CLI command (ingest_shifts) and the dashboard's upload button call the _same_ underlying service function (shifts/ingestion.py), so a dataset loaded at startup and one uploaded by a user mid-session are held to identical standards — there is no "trusted" and "untrusted" code path.

---

## 6. Installation & Setup

### 6.1 Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) PostgreSQL 13+ if you don't want SQLite

### 6.2 Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **If pip install can't find a matching Django version** (some corporate/regional PyPI mirrors lag behind the public index): requirements.txt uses version _ranges_ (e.g. Django&gt;=5.0,&lt;6.0) specifically so pip can resolve whatever compatible release your mirror actually has. If it still fails, try pip install -r requirements.txt --index-url https://pypi.org/simple to bypass a stale mirror.

Set up the database and load the bundled dataset:

```bash
python manage.py migrate
python manage.py seed_config       # loads activity_config.json + system_config.json
python manage.py ingest_shifts     # cleans and loads data/shift_data.csv as the active dataset
```

(Optional) create an admin user to browse/edit data visually:

```bash
python manage.py createsuperuser
```

Then visit http://localhost:8000/admin/.

**Using PostgreSQL instead of SQLite:**

```bash
export DATABASE_URL="postgres://myuser:mypassword@localhost:5432/shift_analytics"
```

The app detects this and switches the Django database engine automatically — no code changes needed.

### 6.3 Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

.env controls where the frontend looks for the API:

```
VITE_API_BASE_URL=http://localhost:8000/api
```

### 6.4 Running the App

**Terminal 1 — backend:**

```bash
cd backend
source venv/bin/activate
python manage.py runserver 8000
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. The dashboard talks live to http://localhost:8000/api.

**Production build (frontend):**

```bash
npm run build && npm run preview
```

---

## 7. API Reference

Base path: /api.

### 7.1 Filter-Aware Endpoints

These respect the query parameters described in [Section 7.4](#74-filter-query-parameters)and always operate on the **currently active dataset**.

| Endpoint               | Method | Returns                                                                             |
| ---------------------- | ------ | ----------------------------------------------------------------------------------- |
| /dashboard-summary     | GET    | Total hours, productive hours, downtime, efficiency score, record count, date range |
| /shift-analysis        | GET    | Chart-ready blocks for the Gantt timeline                                           |
| /activity-distribution | GET    | Hours and percentage per activity                                                   |
| /breakdown-trend       | GET    | Failure-category hours per day                                                      |
| /insights              | GET    | Auto-generated insight cards                                                        |
| /filter-options        | GET    | Available reasons, categories, date/duration bounds, full activity config list      |

### 7.2 Whole-Dataset Endpoints

These **ignore all filter query parameters by design** (see [Section 8.4](#84-why-breakdown-streaks--data-quality-ignore-filters)) and always summarize the entire active dataset.

| Endpoint             | Method | Returns                                                                            |
| -------------------- | ------ | ---------------------------------------------------------------------------------- |
| /breakdown-streaks   | GET    | Detected streaks, a day-by-day failure timeline, and the thresholds used           |
| /data-quality-report | GET    | Validity percentage, record counts, hours stats, category count, anomaly breakdown |

### 7.3 Dataset Management Endpoints

| Endpoint                      | Method | Description                                                                                                                       |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------- |
| /datasets                     | GET    | Lists every dataset ever ingested (bundled + uploads), most recent first                                                          |
| /datasets/upload              | POST   | Multipart upload, field name "file" (.csv only). Cleans, ingests, and **activates** the new dataset. Returns the cleaning report. |
| /datasets/&lt;id&gt;/activate | POST   | Switches the active dataset back to a previously ingested one                                                                     |

Example upload via curl:

```bash
curl -F "file=@my_shift_data.csv" http://localhost:8000/api/datasets/upload
```

### 7.4 Filter Query Parameters

All optional, combinable, used only by the filter-aware endpoints above:

| Param                      | Format                         | Example                                  |
| -------------------------- | ------------------------------ | ---------------------------------------- |
| date_from, date_to         | YYYY-MM-DD                     | ?date_from=2025-10-01&date_to=2025-10-10 |
| reason                     | comma-separated activity names | ?reason=Breakdown,Power Failure          |
| category                   | comma-separated category names | ?category=Failure                        |
| min_duration, max_duration | hours (float)                  | ?min_duration=1&max_duration=5           |

---

## 8. Key Design Decisions

This section explains the _why_ behind the implementation, not just the _what_ — the reasoning a reviewer would want to see.

### 8.1 No Hardcoding — The Configuration System

The project brief's central constraint was: **no activity name, threshold, or business rule may be hardcoded into application logic.** This is enforced architecturally, not just by convention:

- ActivityConfiguration (one row per activity name) holds productive_status, category, and display_color. Seeded from config_app/data/activity_config.json, but editable via Django admin or the database directly.
- SystemConfiguration is a generic key/value store for every numeric threshold the app uses (breakdown streak minimums, severity cutoffs, efficiency target, etc.), seeded from system_config.json.
- **All reads go through config_app/loader.py** — get_or_register_activity() and get_setting_float()/get_setting_int(). No other module imports these models directly for read access. This means there is exactly one chokepoint between "a string from the dataset" and "a business decision," and changing a rule never requires touching Python code.
- **Unknown activities are never dropped.** If an uploaded dataset contains a REASON value the system hasn't seen before, it's auto-registered with safe defaults (productive=False, category="Uncategorized") and flagged in the UI legend with an "auto" badge, so a manager can classify it properly rather than losing the data or crashing the pipeline.

### 8.2 Data Quality & Cleaning Assumptions

Real shift logs are messy. The cleaning pipeline (shifts/cleaning.py) makes these explicit, documented decisions:

1. **A row is dropped only if unrecoverable** — no parseable date AND no way to establish both a start and end time. Everything else is repaired.
2. **Missing START or END (not both)** is derived from the other timestamp plus or minus HOURS, when HOURS is present and positive.
3. **Malformed DAY_DATE** (e.g. an impossible month/day) is derived from the valid START timestamp instead of dropping the row.
4. **Unparseable timestamp strings** are treated as missing, then handled by rule 2.
5. **END before START** is treated as an overnight shift and rolled forward a day — _unless_ that implies more than 16 continuous hours, in which case the record is rejected as implausible.
6. **HOURS vs. END minus START mismatches** (including negative, zero, or non-numeric HOURS) are recalculated from the timestamps, since timestamps are the more granular, less error-prone source. A 3-minute tolerance absorbs rounding before triggering a recalculation.
7. **Missing REASON** becomes "Unspecified" rather than being dropped, so the hours aren't lost from totals.
8. **Exact duplicates** (same date, start, end, reason) are removed, keeping the first occurrence.

Separately from these _repairs_, the pipeline also counts **anomalies**purely for reporting (these don't change what gets kept, only what gets flagged in the Data Quality Report):

- **Zero-hour records** — the raw HOURS value was exactly 0.
- **Negative-hour records** — the raw HOURS value was negative (counted before correction, since this describes how messy the _source_ data was).
- **Statistical outliers** — any cleaned record at or above the 95th percentile of cleaned shift durations.
- **Duplicate records** — same count as cleaning's duplicate removal.

Every run's full decision log and summary counts are persisted in a DataQualityReport row, so cleaning behavior is auditable, not a black box.

### 8.3 Dynamic Dataset Upload

The dashboard isn't locked to the bundled CSV. A Dataset model tracks every file ever ingested; exactly one is is_active at a time, and the entire API serves data from whichever one is active. Uploading a new CSV:

1. Runs through the identical cleaning and configuration pipeline as the default dataset (same ingest_dataframe() function).
2. Is stored as a **new** Dataset row — the previous one is deactivated, not deleted, so you can switch back via "Switch" in the dataset panel or POST /api/datasets/&lt;id&gt;/activate.
3. Immediately becomes what every chart, KPI, and report on the dashboard reflects.

This means the bundled dataset is genuinely just the _default_, not a special case in the code.

### 8.4 Why Breakdown Streaks & Data Quality Ignore Filters

Every other panel on the dashboard respects the active filters (date range, activity, category, duration) — that's the point of a filter panel. **Breakdown Streaks and the Data Quality Report deliberately do not.** The reasoning:

- **Breakdown risk is a standing operational fact.** If a manager filters down to look at "Training" activities only, the breakdown streak that happened last Tuesday didn't stop happening — showing it as "no streaks" because of an unrelated filter would be actively misleading. This panel always answers "where in the _entire_ dataset did breakdowns cluster," independent of whatever else is being explored elsewhere.
- **Data quality is a historical fact about the dataset as ingested**, not a property of any particular filtered slice. Asking "is this data trustworthy" shouldn't have a different answer depending on which date range you happen to have selected.

Both endpoints are implemented to literally ignore the filter query parameters at the view layer (\_active_dataset_queryset() vs. \_base_queryset(request) in shifts/views.py), and this behavior is covered by tests (test_breakdown_streaks_endpoint_ignores_filters, test_data_quality_report_endpoint_ignores_filters).

### 8.5 Breakdown Streak Detection Algorithm

A "breakdown streak" is not strictly consecutive rows in the dataset — real logs interleave failures with productive/idle time, and a manager cares about _recurring_ failures within a practical window, not just back-to-back rows. The algorithm (shifts/analytics.compute_breakdown_streaks):

1. Filters to Failure-category events only (by **category**, so it generalizes to any activity tagged Failure, known or auto-registered).
2. Sorts chronologically by (date, start_time).
3. Groups events into a streak as long as the gap between one event's end and the next failure event's start is **at most max_gap_hours** (default 6h). A larger gap ends the current streak and starts a new one.
4. A streak is only _reported_ if it has **at least minimum_events** (default 2) AND **at least minimum_hours** cumulative duration (default 4h).
5. Each reported streak is classified into a **severity** (Low / Medium / High / Critical) based on its average failure-hours per calendar day spanned, against configurable thresholds (streak_severity_critical_avg_hours, etc. in SystemConfiguration).

All five thresholds live in SystemConfiguration and can be tuned per plant without a code change. Against the bundled sample dataset, these defaults correctly surface two real streaks — for example, three failure events on a single day totalling 9.1 hours (Critical severity) — rather than either missing them or over-flagging noise.

### 8.6 Operational Insights Are Computed, Not Written

shifts/insights.py never returns a fixed sentence. Every insight card has the shape:

```json
{
  "title": "Operational Efficiency Status",
  "metric": "77.13%",
  "text": "Current operational efficiency is 77.13% (good). Productive hours: 99.5 / 129.0 total hours.",
  "action": "Focus on reducing minor breakdowns and optimizing shift schedules.",
  "severity": "Medium"
}
```

Every number in text, metric, and the severity classification is pulled live from the analytics engine for whatever data and filters are currently active — change the dataset, change the filters, and the wording, the numbers, and the severities all change with it. This is verified by a test (test_insights_are_generated_from_data_and_include_severity) that asserts every insight's text contains at least one digit, which would fail immediately if a card were ever hardcoded.

Insight cards currently generated:

- **Operational Efficiency Status** — efficiency percentage vs. the configurable target, with a tailored action depending on whether it's met.
- **Breakdown Risk Assessment** — references the active breakdown streak (if any) plus total failure incident counts, with an action naming the actual leading failure activity.
- **Optimization Opportunity** — the largest non-failure, non-productive time sink (e.g. Logistics, Idle), so managers see where else time leaks.
- **Unclassified Activity Detected** — flags any auto-registered/ Uncategorized activity so it gets properly classified.

### 8.7 Visual Design Direction

The UI is built as an industrial control-room / HMI panel rather than a generic SaaS dashboard template: graphite panel surfaces, an amber signal-light accent, hairline dividers, near-zero border radius, a condensed display face (Oswald) for headings, and a tabular monospace (IBM Plex Mono) for every number so columns of hours/percentages align. All data-series colors (activity categories) come from the API's display_color field, never frontend CSS — one color system shared between backend configuration and frontend rendering.

---

## 9. Usage Guide

### 9.1 Exploring the Default Dataset

On first load, the dashboard shows the bundled shift_data.csv — no setup required beyond the install steps in [Section 6](#6-installation--setup). The **Dataset panel** (top of the left sidebar) confirms which dataset is active and how many records it contains.

### 9.2 Uploading Your Own Dataset

1. Click **Upload new CSV** in the Dataset panel.
2. Choose a CSV with the columns DAY_DATE, START, END, HOURS, REASON (extra/differently-ordered columns and unfamiliar REASON values are both handled gracefully — see [Section 8.1](#81-no-hardcoding--the-configuration-system)and [Section 8.2](#82-data-quality--cleaning-assumptions)).
3. The dashboard immediately switches to the new dataset and shows how many records were cleaned (e.g. "Loaded 'new.csv' — 47 clean records.").
4. To go back to a previous dataset, scroll to **Previously loaded** in the Dataset panel and click **Switch** next to it. Nothing is ever deleted by uploading something new.

### 9.3 Filtering & Drilling In

Use the **Filters** panel to narrow the KPI cards, Shift Analysis chart, Activity Distribution, Breakdown Trend, and Operational Insights to a date range, specific activities, categories, or duration range. Multiple filters combine (AND logic). Click **Clear all filters** to reset.

> Breakdown Streaks and the Data Quality Report panels do **not** change when you filter — see [Section 8.4](#84-why-breakdown-streaks--data-quality-ignore-filters)for why that's intentional, not a bug.

### 9.4 Reading the Breakdown Streaks Panel

The bar chart shows failure hours per day across the _entire_ active dataset; days that fall inside a detected streak are highlighted with a red background band. Click a date tab below the chart to see that streak's full detail card: Start Date, End Date, Duration (Days), Total Hours, Avg/Day, Severity, and which activities were involved.

### 9.5 Reading the Data Quality Report

- **Data Validity** — the headline percentage and gauge bar.
- **Stat grid** — Total/Valid/Invalid Records, Total Hours, Avg Shift Duration, and how many distinct Categories exist in the data.
- **Anomalies Detected** — a checklist of zero-hour records, negative-hour records, statistical outliers (95th+ percentile), and duplicate records found during cleaning.

### 9.6 Reading Operational Insights

Each card has a title, a large headline metric, an explanatory sentence, a colored severity badge (Low/Medium/High/Critical), and a suggested **Action** — read the Action line first if you're short on time; it's the one-sentence "what to actually do" for that card.

### 9.7 Reconfiguring Activities & Thresholds

Open http://localhost:8000/admin/ (requires createsuperuser, see [Section 6.2](#62-backend-setup)) to:

- Edit any ActivityConfiguration row — change its category, productivity flag, or color, including ones that were auto-registered from an upload.
- Edit any SystemConfiguration row — tune breakdown streak thresholds, severity cutoffs, or the efficiency target percentage.

Changes take effect on the next API request — no restart needed.

---