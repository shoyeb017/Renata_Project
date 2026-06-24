# Shift Ops Console — Employee Shift Operational Analytics Dashboard

A full-stack web application that turns raw, messy employee shift logs into an operational picture a plant manager can act on: an efficiency score, downtime breakdown, breakdown-streak detection, a data-quality audit, and auto-generated insights — all driven by configuration stored in the database, never hardcoded into the application logic.

> **New here?** Jump straight to [Quick Start](#3-installation--setup) to get the app running, or [Usage Guide](#9-usage-guide) to see how to use it once it's up.

---

## Table of Contents

 1. [What This Project Does](#1-what-this-project-does)
 2. [Features](#2-features)
 3. [Installation & Setup](#3-installation--setup)
 4. [Technology Stack](#4-technology-stack)
 5. [Project Structure](#5-project-structure)
 6. [The Data Pipeline](#6-the-data-pipeline)
 7. [API Reference](#7-api-reference)
 8. [Key Design Decisions](#8-key-design-decisions)
 9. [Usage Guide](#9-usage-guide)
10. [Testing](#10-testing)
11. [Assumptions Log](#11-assumptions-log)
12. [Known Limitations](#12-known-limitations)

---

## 1. What This Project Does

Plant managers receive shift logs (date, start time, end time, hours, and a free-text "reason" — Training, Breakdown, Power Failure, etc.) and need to answer questions like:

- How efficiently is the shift running, and is that improving?
- Where is time actually going — productive work vs. failures vs. idle time?
- Is there a *pattern* of repeated breakdowns, or are failures one-off?
- How trustworthy is this data — how much of it had to be cleaned or guessed at?
- What should I actually *do* about any of this?

This application answers all five, automatically, from whatever shift CSV is loaded — including a CSV the user uploads themselves at runtime, with no code changes or restarts required.

---

## 2. Features

- **Dynamic dataset upload.** Drop in any shift CSV from the dashboard sidebar; the app cleans it, classifies its activities, and switches the entire dashboard to that data immediately. The originally bundled dataset is never deleted — you can switch back to it (or any previous upload) with one click.
- **Operational Efficiency Score**, computed live as `Productive Hours ÷ Total Hours × 100`.
- **Shift Analysis chart** — a Gantt/timeline visualization (not a bar chart) showing every shift block positioned by date and time-of-day, on a continuous 0–36 hour scale so overnight shifts render without clipping or wrapping.
- **Activity Distribution** and **Breakdown Trend** charts, both filterable by date range, activity, category, and duration.
- **Breakdown Streak detection** — finds clusters of failure events that recur within a configurable time window, reports each as a severity- rated incident (Low/Medium/High/Critical), and visualizes exactly where in the timeline they occurred. **This panel always reflects the entire active dataset, deliberately ignoring the dashboard's interactive filters** — breakdown risk is a standing operational fact, not something that should disappear because of an unrelated filter selection.
- **Data Quality Report** — validity percentage, record counts, and an anomaly breakdown (zero-hour records, negative-hour records, statistical outliers via the 95th percentile, duplicate rows). Also whole-dataset, also filter-independent, for the same reason as above.
- **Operational Insights** — plant-manager-facing cards (Efficiency Status, Breakdown Risk, Optimization Opportunities, Configuration flags) that **do** respond to filters and to whichever dataset is active. Every number in every insight is computed live; no insight text is a static template.
- **Zero hardcoding.** Every activity name, its productivity flag, its category, its chart color, and every numeric threshold (streak sensitivity, severity bands, efficiency target) lives in the database, seeded from JSON. New/renamed/unexpected activity names are auto-registered with safe defaults instead of crashing or being dropped.

---

## 3. Installation & Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) PostgreSQL 13+ — SQLite is used by default, zero config needed

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **If** `pip install` **can't find a matching Django version** (some corporate/regional PyPI mirrors lag behind the public index): `requirements.txt` uses version *ranges* (e.g. `Django>=5.0,<6.0`) specifically so pip can resolve whatever compatible release your mirror actually has. If it still fails, try `pip install -r requirements.txt --index-url https://pypi.org/simple`, or run `pip index versions django` to see what your index offers.

Set up the database, seed the configuration tables, and load the bundled dataset:

```bash
python manage.py migrate
python manage.py seed_config       # loads activity_config.json + system_config.json
python manage.py ingest_shifts     # cleans and loads data/shift_data.csv as the active dataset
```

(Optional) create an admin user to browse/edit data visually:

```bash
python manage.py createsuperuser
```

Start the API server:

```bash
python manage.py runserver 8000
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`. The dashboard talks to `http://localhost:8000/api` by default (configurable via `VITE_API_BASE_URL`in `.env`).

### Using a Different Dataset From the Start

Two ways, both equally valid:

1. **From the UI** (recommended): once the app is running, use the **Upload new CSV** button in the sidebar. See [Usage Guide §1](#1-data-upload).
2. **From the command line**, before ever opening the dashboard:

   ```bash
   export DATASET_PATH=/path/to/your_other_shift_data.csv
   python manage.py ingest_shifts --reset
   ```

---

## 4. Technology Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Backend framework | Django + Django REST Framework | Batteries-included ORM, admin, and migrations; DRF gives a clean `@api_view` surface for a small, well-defined API |
| Database | SQLite (default) / PostgreSQL (optional) | Zero-config local dev; swappable to Postgres via one `DATABASE_URL` env var for production, no code changes |
| Data processing | Pandas + NumPy | Vectorized cleaning, percentile calculations (outlier detection), groupby aggregations for all chart data |
| Frontend framework | React 19 + Vite | Fast dev server, component-based architecture as required |
| Charting | Recharts (pie, area) + hand-built SVG (Gantt timeline, streak chart) | Recharts has no first-class Gantt chart type, so the two most bespoke visualizations are custom SVG — documented as a deliberate exception |
| Routing | React Router | Future-proofs the single-page dashboard for additional routes |
| Testing | Django `TestCase` (backend) / Vitest + React Testing Library (frontend) | Standard, well-supported tooling for each stack |

---

## 5. Project Structure

```
backend/
├── shift_analytics/          Django project root (settings, root urls)
├── config_app/                Configuration: WHAT activities mean
│   ├── data/                    activity_config.json, system_config.json (seed files)
│   ├── models.py                ActivityConfiguration, SystemConfiguration
│   ├── loader.py                single access point for all config reads
│   └── management/commands/seed_config.py
├── shifts/                    Domain logic: WHAT happened and what it implies
│   ├── models.py                Dataset, ShiftRecord, DataQualityReport
│   ├── cleaning.py              Data Quality Module - validation & repair
│   ├── ingestion.py             Shared ingest pipeline (CLI command + upload API both use this)
│   ├── analytics.py             Analytics Engine - all computed metrics
│   ├── insights.py              Insight-card generator
│   ├── filters.py               Dynamic query-param filter system
│   ├── views.py / urls.py       REST API
│   ├── tests.py                 Backend test suite
│   └── management/commands/ingest_shifts.py
└── data/shift_data.csv        Bundled default dataset

frontend/
└── src/
    ├── api/client.js              REST client - every API call goes through here
    ├── hooks/useDashboardData.js  Central data + filter + dataset state
    ├── components/
    │   ├── DatasetPanel.jsx          Upload / switch dataset
    │   ├── FilterPanel.jsx           Dynamic filters (date, reason, category, duration)
    │   ├── KpiCards.jsx               Efficiency score + headline KPIs
    │   ├── ShiftAnalysisChart.jsx     Custom Gantt-style timeline (the primary chart)
    │   ├── ActivityLegend.jsx        Auto-updating legend from live config
    │   ├── ActivityDistributionChart.jsx
    │   ├── BreakdownTrendChart.jsx
    │   ├── BreakdownStreaksPanel.jsx  Whole-dataset streak visual + detail cards
    │   ├── DataQualityReportPanel.jsx Whole-dataset quality/anomaly report
    │   └── InsightPanel.jsx          Severity-rated, data-derived insight cards
    ├── pages/Dashboard.jsx        Composes everything above
    └── test/                      Vitest + React Testing Library specs
```

**Why this split:** `config_app` owns *what activities mean* (is "Breakdown" productive? what color is it? what category does it roll up into?). `shifts` owns *what happened and what it implies* (the actual records, and every metric derived from them). Nothing in `shifts` ever needs to change when activities are renamed, merged, or invented - it always asks `config_app.loader` for the answer, and unknown activities are auto-registered rather than rejected.

---

## 6. The Data Pipeline

```
  Raw CSV (bundled or uploaded)
        |
        v
  Ingestion           shifts/ingestion.py  - reads the CSV into a DataFrame
        |
        v
  Validation &        shifts/cleaning.py   - detects missing values, bad
  Cleaning                                    timestamps, duration mismatches,
        |                                     duplicates, statistical anomalies
        v
  Configuration        config_app/loader.py - every activity name resolved
  Rules                                        against the DB; unknowns auto-
        |                                       registered with safe defaults
        v
  Database             A new Dataset row is created; ShiftRecords are bulk-
  Persistence                                  inserted under it; a
                                                 DataQualityReport is logged
        |
        v
  Analytics Engine     shifts/analytics.py  - efficiency score, distributions,
                                                trend lines, streak detection
        |
        v
  REST API             shifts/views.py      - JSON endpoints, some filter-aware,
                                                some intentionally whole-dataset
        |
        v
  React Dashboard       frontend/src        - charts, filters, upload UI
        |
        v
  Operational Insights  shifts/insights.py  - severity-rated, data-derived
                                                recommendations
```

Both the bundled dataset and a user's uploaded CSV travel through **exactly this same pipeline** — there is no separate "demo data" code path. See `backend/shifts/ingestion.py`: the management command and the upload API endpoint both call `ingest_dataframe()`.

---

## 7. API Reference

Base path: `/api`.

### Filter-Aware Endpoints

These respect the optional query parameters below and reflect whatever the dashboard's filter panel is currently set to.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/dashboard-summary` | GET | Total/productive/downtime hours, efficiency score, record count, date range |
| `/shift-analysis` | GET | Chart-ready blocks for the Gantt timeline |
| `/activity-distribution` | GET | Hours & % per activity |
| `/breakdown-trend` | GET | Failure-category hours per day |
| `/insights` | GET | Auto-generated, severity-rated insight cards |
| `/filter-options` | GET | Available reasons, categories, date/duration bounds, full activity config - for the *active* dataset |

**Filter query parameters** (all optional, combinable):

| Param | Format | Example |
| --- | --- | --- |
| `date_from`, `date_to` | `YYYY-MM-DD` | `?date_from=2025-10-01&date_to=2025-10-10` |
| `reason` | comma-separated activity names | `?reason=Breakdown,Power Failure` |
| `category` | comma-separated category names | `?category=Failure` |
| `min_duration`, `max_duration` | hours (float) | `?min_duration=1&max_duration=5` |

### Whole-Dataset Endpoints

These **ignore all filter query parameters by design** — they always reflect the complete active dataset.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/breakdown-streaks` | GET | Detected streaks (with severity), plus a full failure-hours timeline for visualization |
| `/data-quality-report` | GET | Validity %, record counts, aggregate stats, anomaly breakdown |

### Dataset Management

| Endpoint | Method | Description |
| --- | --- | --- |
| `/datasets` | GET | Lists every dataset ever ingested (bundled default + uploads), newest first |
| `/datasets/upload` | POST (multipart, field `file`) | Uploads a CSV, runs it through the full pipeline, activates it |
| `/datasets/<id>/activate` | POST | Switches the active dataset to a previously ingested one |

Example:

```
GET /api/dashboard-summary?category=Failure&date_from=2025-10-01
POST /api/datasets/upload   (multipart/form-data, field name "file")
POST /api/datasets/3/activate
```

---

## 8. Key Design Decisions

### 8.1 No Hardcoding — Enforced Structurally, Not Just By Convention

Every activity name, productivity flag, category, and color lives in `ActivityConfiguration` (DB table, seeded from `activity_config.json`). Every numeric threshold (breakdown streak sensitivity, severity bands, efficiency target) lives in `SystemConfiguration` (seeded from `system_config.json`). All reads go through `config_app/loader.py` — there is exactly one chokepoint between "a string from the dataset" and "a business decision." Application code never contains `if activity == "Breakdown"`.

**Unknown activities are auto-registered, not rejected.** If a dataset contains an activity name never seen before, it's inserted into `ActivityConfiguration` with safe defaults (`productive=False, category="Uncategorized"`) and flagged `is_auto_registered=True` so a manager can see it in the legend (tagged `auto`) and reclassify it later — the dashboard keeps working immediately either way.

### 8.2 Dynamic Dataset Upload, Not Just a Static File

Rather than the app being tied to one CSV on disk, `Dataset` is a first-class database model. Each upload (or the bundled CSV) becomes its own `Dataset` row; exactly one is `is_active` at a time, and that's what every endpoint serves. Uploading a new file **does not delete previous data** — it's still in the database, switchable back to with one click. This is what makes "upload new data, but keep the default available" work without any special-casing.

### 8.3 Why Breakdown Streaks and Data Quality Are Filter-Independent

Every other panel responds to the filter bar, because filtering is how a manager narrows their *view*. But breakdown risk and data trustworthiness are properties of the *dataset itself*, not of a view — if a manager filters down to "show me only Training records this week," the breakdown streak panel showing "0 incidents" would be misleading, not insightful. These two panels are deliberately wired to a separate, unfiltered query path (`_active_dataset_queryset()` in `views.py`, with no `apply_filters()`call) so they always answer "what's the real state of this plant," full stop.

### 8.4 Breakdown Streak Detection Algorithm

A "streak" is a maximal run of Failure-category events where the gap between one event's end and the next failure event's start is **≤** `max_gap_hours` (default 6h). This treats "recurring failures" as failures that cluster within a practical time window — not strictly back-to-back CSV rows — since that's the signal a plant manager actually cares about (e.g. flapping equipment across a shift). A streak is only *reported* if it has **≥** `minimum_events` (default 2) and **≥** `minimum_hours` (default 4h) of cumulative impact, to avoid flagging two unrelated failures hours apart as a "streak." Each qualifying streak is then classified by **average impact hours per calendar day spanned**against configurable severity bands:

| Severity | Avg hours/day |
| --- | --- |
| Critical | ≥ 8h |
| High | ≥ 5h |
| Medium | ≥ 2h |
| Low | below 2h |

All five numbers above are `SystemConfiguration` rows, not constants in the code — tune them per plant without touching a single line.

### 8.5 Data Quality Anomaly Detection

During cleaning, four anomaly counters are tracked independently of whatever repair action was taken on a row:

- **Zero hours** — the raw `HOURS` value was exactly 0.
- **Negative hours** — the raw `HOURS` value was negative.
- **Outliers (95th percentile)** — after cleaning, any record whose duration sits at or above the 95th percentile of all cleaned durations.
- **Duplicates** — exact repeats (same date, start, end, reason), removed during cleaning.

These are diagnostic facts about how messy the *source* data was, reported separately from the cleaning pipeline's repair actions — so a manager can see both "how dirty was this CSV" and "what did the system do about it."

### 8.6 Operational Insights Are Computed, Not Templated

Every insight card (`Operational Efficiency Status`, `Breakdown Risk Assessment`, `Optimization Opportunity`, `Unclassified Activity Detected`) interpolates real numbers from the analytics engine for whatever filtered view is currently active. Severity badges and "Action:" recommendations are derived from those same numbers (e.g. severity escalates as efficiency drops below threshold, or as an active streak's severity increases) — they are not fixed strings keyed off a category. Change the filters or upload a different dataset, and every word and number on this panel changes with it.

### 8.7 Visual Identity

The UI is built as an industrial control-room / HMI panel rather than a generic SaaS dashboard template: graphite panel surfaces, an amber signal-light accent, hairline dividers, near-zero border radius, a condensed display face (Oswald) paired with a tabular monospace (IBM Plex Mono) so every column of numbers aligns. All data-series colors come from the API's `display_color` field — never hardcoded in frontend CSS — keeping one color system shared between backend config and frontend rendering.

---

## 9. Usage Guide

### 1. Data Upload

On load, the dashboard shows the **bundled default dataset**(`shift_data.csv`) automatically — no setup required. To analyze your own data:

1. Click **Upload new CSV** in the sidebar's Dataset panel.
2. Select a CSV with columns `DAY_DATE, START, END, HOURS, REASON`.
3. The app cleans it, classifies its activities (auto-registering any new ones), and switches the **entire dashboard** to that data within seconds.
4. Your previous dataset (including the original default) is preserved — it appears under **Previously loaded**, with a **Switch** button to revert at any time.

### 2. Filter & Analyze

Use the **Filters** panel to narrow by date range, activity reason, category, or duration. The KPI cards, Shift Analysis chart, Activity Distribution, Breakdown Trend, and Operational Insights all update live. (Breakdown Streaks and the Data Quality Report intentionally do **not** change — see §8.3 above.)

### 3. View Insights

Scroll to **Operational Insights** for plant-manager-facing recommendations, each with a severity badge and a concrete next step. These respond to both your current filters and whichever dataset is active.

### 4. Investigate Breakdown Streaks

The **Breakdown Streaks** panel shows a timeline bar chart of failure hours across the whole dataset, with detected streak periods shaded. Click a streak's tab (labeled by start date and severity) to see its full detail card: start/end date, duration in days, total hours, average hours/day, severity, and which activities were involved.

### 5. Audit Data Quality

The **Data Quality Report** panel shows the dataset's validity percentage, record counts, aggregate stats, and a breakdown of detected anomalies (zero-hour records, negative-hour records, statistical outliers, duplicates) — a quick gut-check on how trustworthy the loaded data is.

---

## 10. Testing

### Backend — 40 tests

```bash
cd backend
python manage.py test shifts -v 2
```

Covers: data cleaning (missing values, malformed dates, invalid timestamps, overnight shifts, duration mismatches, duplicates, zero/ negative/outlier anomaly counting), the analytics engine (efficiency calculation, distribution percentages, streak detection with severity, data quality report shape), config auto-registration, the dataset ingestion service (upload creates a new active dataset, switching deactivates the previous one without deleting it), and the full API surface — including explicit tests that `/breakdown-streaks` and `/data-quality-report` return identical results regardless of filter query parameters.

### Frontend — 25 tests

```bash
cd frontend
npm test
```

Covers component rendering and behavior for KPI cards, the dynamic filter panel (chip toggling, reset visibility), the Gantt chart's required axis labels, the dataset upload/switch panel, the insight cards' severity display, the data quality report's anomaly list, and the breakdown streaks detail view.

---

## 11. Assumptions Log

### Cleaning (`shifts/cleaning.py`)

1. A row is dropped only if unrecoverable: no parseable date **and** no way to establish both a start and end time.
2. Missing START or END (not both): derived from the other timestamp ± `HOURS`.
3. Malformed `DAY_DATE` with a valid `START`: date derived from `START`instead of dropping the row.
4. Unparseable timestamp strings are treated as missing, then handled by rule 2.
5. `END` before `START` is treated as an overnight shift (rolled forward one day) **unless** that implies more than 16 continuous hours, in which case it's rejected as implausible.
6. `HOURS` vs. `END - START` mismatches beyond a 3-minute tolerance are recalculated from timestamps (the more granular, less error-prone source).
7. Missing `REASON` becomes `"Unspecified"` rather than being dropped, so the hours aren't lost from totals.
8. Exact duplicates (same date, start, end, reason) are removed, keeping the first occurrence.
9. Anomaly counters (zero/negative hours) reflect the **raw** `HOURS`value as supplied, even though the row itself gets repaired and kept. Outliers are flagged post-cleaning, at or above the 95th percentile of cleaned durations.

### Breakdown Streaks (`shifts/analytics.py`)

See §8.4 above for the full algorithm and severity bands.

### Insights (`shifts/insights.py`)

Efficiency severity escalates as the score falls further below the configured low-efficiency threshold (`efficiency_low_threshold_pct`, default 70%). Breakdown risk severity inherits directly from the most significant currently-active streak. Optimization-opportunity severity is `Medium` once a non-failure, non-productive category exceeds 15% of total hours, `Low` otherwise — all of which are computed thresholds, not hardcoded text.

---

## 12. Known Limitations

- The Gantt timeline and breakdown-streak timeline are hand-rolled SVG components rather than charting-library components, since neither Recharts, ECharts, nor D3-via-React ships a ready-made Gantt chart — flagged here as an explicit, deliberate exception to "use a charting library for everything."
- Authentication is not implemented — this is an internal-tool MVP. Add DRF's `IsAuthenticated` plus a session/token scheme before exposing this outside a trusted network.
- Uploaded datasets are kept indefinitely (by design, so users can switch back). For long-running production use, consider adding a retention/ cleanup policy for old uploads.