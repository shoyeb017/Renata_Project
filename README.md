# Shift Ops Console — Employee Shift Operational Analytics Dashboard

A full-stack analytics application that turns raw, messy shift-log data
into an operational picture a plant manager can act on: efficiency score,
downtime breakdown, breakdown streak detection, failure timing patterns,
and auto-generated insights — all driven by configuration, not hardcoded
business logic.

```
Raw Dataset → Ingestion → Validation/Cleaning → Configuration Rules
            → Analytics Engine → REST API → React Dashboard → Insights
```

---

## 1. Project overview

**Backend:** Django + Django REST Framework, SQLite by default (swappable
to PostgreSQL via one environment variable). Pandas/NumPy power the data
cleaning and analytics modules.

**Frontend:** React 19 + Vite, Recharts for the standard charts, and a
hand-built SVG component for the primary Gantt-style "Shift Analysis"
timeline (Recharts has no first-class Gantt chart type, so this one
visualization is custom SVG — documented here as a deliberate exception
to "use a charting library for everything").

**Core design rule — no hardcoding:** every activity name, productivity
flag, category, color, and business threshold (breakdown streak minimums,
efficiency target, etc.) lives in the database, seeded from JSON config
files. Application code never contains a string comparison like
`if reason == "Breakdown"`. See [Section 6](#6-dynamic-configuration) for
how this is enforced architecturally.

---

## 2. Architecture

```
backend/
├── shift_analytics/        Django project (settings, root urls)
├── config_app/             ActivityConfiguration & SystemConfiguration models
│   ├── data/                 activity_config.json, system_config.json (seeds)
│   ├── loader.py             SINGLE access point for all config reads
│   └── management/commands/seed_config.py
├── shifts/                 ShiftRecord model, pipeline, analytics, API
│   ├── cleaning.py           Data Quality Module (Phase 4)
│   ├── analytics.py          Analytics Engine (Phase 6)
│   ├── insights.py           Insight generator (Phase 10)
│   ├── filters.py            Dynamic filter system (Phase 7)
│   ├── views.py / urls.py    REST API (Phase 7)
│   ├── tests.py              Backend test suite (Phase 11)
│   └── management/commands/ingest_shifts.py
└── data/shift_data.csv     Default dataset (swappable, see Section 5)

frontend/
├── src/
│   ├── api/client.js          REST client, all calls go through here
│   ├── hooks/useDashboardData.js   Central data + filter state
│   ├── components/            KpiCards, FilterPanel, ShiftAnalysisChart,
│   │                          ActivityDistributionChart, BreakdownTrendChart,
│   │                          FailureHeatmap, BreakdownStreaks, InsightPanel,
│   │                          ActivityLegend, AppHeader
│   ├── pages/Dashboard.jsx    Composes everything above
│   ├── styles/tokens.css      Design tokens (see Section 8)
│   └── test/                  Vitest + React Testing Library specs
```

**Why this split:** `config_app` owns *what activities mean*;
`shifts` owns *what happened and what it implies*. Nothing in `shifts`
ever needs to change when activity categories are renamed, merged, or
invented — it always asks `config_app.loader` for the answer.

---

## 3. Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) PostgreSQL 13+ if you don't want SQLite

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **If `pip install` can't find a matching Django version** (some
> corporate/regional PyPI mirrors lag behind the public index): the
> `requirements.txt` uses version *ranges* (e.g. `Django>=5.0,<6.0`)
> specifically so pip can resolve whatever compatible release your mirror
> actually has — it doesn't need an exact build. If it still fails, try
> `pip install -r requirements.txt --index-url https://pypi.org/simple`
> to bypass a stale mirror, or run `pip index versions django` to see
> what your configured index has available.

### Frontend

```bash
cd frontend
npm install
```

---

## 4. Environment setup

Copy the example env files and adjust as needed:

```bash
cd frontend
cp .env.example .env
```

| Variable | Where | Purpose | Default |
|---|---|---|---|
| `DATASET_PATH` | backend (shell env) | Path to the source CSV | `backend/data/shift_data.csv` |
| `DATABASE_URL` | backend (shell env) | `postgres://user:pass@host:port/db` to use Postgres | unset → SQLite |
| `DJANGO_SECRET_KEY` | backend | Django secret key | dev key (change for production) |
| `DJANGO_DEBUG` | backend | `True`/`False` | `True` |
| `DJANGO_ALLOWED_HOSTS` | backend | Comma-separated hosts | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | backend | Comma-separated origins allowed to call the API | `http://localhost:5173,http://127.0.0.1:5173` |
| `VITE_API_BASE_URL` | frontend (`.env`) | Where the React app finds the API | `http://localhost:8000/api` |

---

## 5. Database setup

### SQLite (default — zero config)
Nothing to do. `db.sqlite3` is created in `backend/` on first migrate.

### PostgreSQL
```bash
export DATABASE_URL="postgres://myuser:mypassword@localhost:5432/shift_analytics"
```
The app parses this and switches the Django `DATABASES` engine automatically
— no code changes required (see `shift_analytics/settings.py`).

### Migrate, seed config, and ingest data
```bash
cd backend
python manage.py migrate
python manage.py seed_config       # loads activity_config.json + system_config.json
python manage.py ingest_shifts     # cleans and loads data/shift_data.csv
```

To use a **different dataset** without touching code:
```bash
export DATASET_PATH=/path/to/your_other_shift_data.csv
python manage.py ingest_shifts --reset   # --reset clears existing ShiftRecord rows first
```
`ingest_shifts` is idempotent: re-running it on the same file does not
create duplicate rows (enforced via a content hash on each cleaned record).
New activity names encountered in any dataset are automatically registered
in `ActivityConfiguration` with safe non-productive defaults — they show up
in the legend tagged `auto` and in the data immediately, with zero code
changes. A plant admin can then edit their category/color/productivity via
Django admin or the database directly.

(Optional) create an admin user to browse data and edit
`ActivityConfiguration` / `SystemConfiguration` visually:
```bash
python manage.py createsuperuser
```
Then visit `http://localhost:8000/admin/`.

---

## 6. Dynamic configuration

Two tables back every business rule in the app:

**`ActivityConfiguration`** — one row per distinct `REASON` value ever seen:
`activity_name`, `productive_status`, `category`, `display_color`,
`is_auto_registered`. Seeded from `config_app/data/activity_config.json`.

**`SystemConfiguration`** — generic key/value store for thresholds:
breakdown streak minimum events/hours/max-gap, efficiency low-threshold,
insight minimum sample size. Seeded from `config_app/data/system_config.json`.

All reads go through `config_app/loader.py`:
- `get_or_register_activity(name)` — look up or auto-register an activity.
- `get_setting_float/int(name, default)` — typed, cached setting lookup.

No other module imports the models directly for read access. This is what
makes the "no hard coding" requirement structural rather than a style
guideline: there is exactly one chokepoint between "a string from the
dataset" and "a business decision," and it's backed by the database.

To add a new activity rule or change a threshold permanently, edit the
JSON seed files and re-run `seed_config --force`, or edit the row directly
via Django admin — both work, since the loader doesn't care which path
created the row.

---

## 7. Running instructions

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

Open `http://localhost:5173`. The dashboard fetches live from
`http://localhost:8000/api` (configurable via `VITE_API_BASE_URL`).

**Production build (frontend):**
```bash
npm run build && npm run preview
```

---

## 8. Design direction

The UI is built as an industrial control-room / HMI panel rather than a
generic SaaS dashboard: graphite panel surfaces, an amber signal-light
accent (`--signal-amber`), hairline dividers, near-zero border radius, and
a condensed display face (Oswald) paired with a tabular monospace
(IBM Plex Mono) for every number so columns of hours/percentages align.
All data-series colors (activity categories) come from the API's
`display_color` field, never from frontend CSS, keeping one color system
shared between backend config and frontend rendering.

---

## 9. API documentation

Base path: `/api`. All endpoints accept the same optional query
parameters for filtering (see below) and return JSON.

| Endpoint | Method | Description |
|---|---|---|
| `/dashboard-summary` | GET | Total hours, productive hours, downtime, efficiency score, record count, date range |
| `/shift-analysis` | GET | Chart-ready blocks for the Gantt timeline (`{blocks: [...]}`) |
| `/activity-distribution` | GET | Hours & % per activity, grouped (`{distribution: [...]}`) |
| `/breakdown-trend` | GET | Failure-category hours per day (`{trend: [...]}`) |
| `/failure-heatmap` | GET | Failure hours by day-of-week × 3-hour bucket (`{heatmap: [...]}`) |
| `/breakdown-streaks` | GET | Detected streaks + the thresholds used (`{streaks: [...], config: {...}}`) |
| `/insights` | GET | Auto-generated insight sentences (`{insights: [...]}`) |
| `/filter-options` | GET | Available reasons, categories, date/duration bounds, full activity config list |

### Filter query parameters (all optional, combinable)

| Param | Format | Example |
|---|---|---|
| `date_from`, `date_to` | `YYYY-MM-DD` | `?date_from=2025-10-01&date_to=2025-10-10` |
| `reason` | comma-separated activity names | `?reason=Breakdown,Power Failure` |
| `category` | comma-separated category names | `?category=Failure` |
| `min_duration`, `max_duration` | hours (float) | `?min_duration=1&max_duration=5` |

Example:
```
GET /api/dashboard-summary?category=Failure&date_from=2025-10-01
```

---

## 10. Cleaning assumptions

The dataset is intentionally messy (missing timestamps, a malformed date,
an unparseable timestamp string, a negative duration, an exact duplicate
row). The cleaning pipeline (`shifts/cleaning.py`) makes these documented
decisions:

1. **A row is dropped only if unrecoverable:** no parseable date AND no way
   to establish both a start and end time. Everything else is repaired.
2. **Missing START or END (not both):** derived from the other timestamp
   ± `HOURS`, when `HOURS` is present and positive.
3. **Malformed `DAY_DATE`** (e.g. `2025-15-55`, an impossible month/day):
   the date is derived from the (valid) `START` timestamp instead of
   dropping the row.
4. **Unparseable timestamp strings** (e.g. `"invalid-time"`): treated as
   missing, then handled by rule 2 above.
5. **`END` before `START`:** treated as an overnight shift and rolled
   forward one day — *unless* that would imply more than 16 continuous
   hours, in which case the record is rejected as implausible rather than
   silently accepted.
6. **`HOURS` vs. `END − START` mismatch** (including negative, zero, or
   non-numeric `HOURS`): recalculated from the timestamps, since
   timestamps are the more granular and less error-prone source. A
   3-minute tolerance absorbs rounding before triggering a recalculation.
7. **Missing `REASON`:** set to `"Unspecified"` rather than dropped, so the
   hours aren't lost from totals; it still appears in the activity
   breakdown so a manager can see how much time is unaccounted-for.
8. **Exact duplicates** (same date, start, end, reason): removed, keeping
   the first occurrence.

Every decision the pipeline makes on a given run is logged and persisted
in a `DataQualityReport` row (`total_records`, `invalid_records`,
`duplicates_removed`, `missing_values_handled`,
`duration_mismatches_fixed`, `final_clean_records`, plus a row-by-row
`details_json`), so cleaning behavior is auditable, not a black box.

---

## 11. Breakdown streak assumptions

A "breakdown streak" is not strictly consecutive rows in the dataset —
real shift logs interleave failures with productive/idle time between
them, and a manager cares about *recurring* failures within a practical
window, not just back-to-back ones. The algorithm
(`shifts/analytics.compute_breakdown_streaks`):

1. Filters to `Failure`-category events only (category, not name — so it
   generalizes to any activity tagged `Failure`, known or auto-registered).
2. Sorts chronologically by `(date, start_time)`.
3. Groups events into a streak as long as the gap between one event's end
   and the next failure event's start is **≤ `max_gap_hours`**
   (default 4h, configurable via `SystemConfiguration`). A larger gap ends
   the current streak and starts a new one.
4. A streak is only *reported* if it has **≥ `minimum_events`** (default 3)
   AND **≥ `minimum_hours`** cumulative duration (default 5h) — this avoids
   flagging two unrelated failures hours apart as a "streak."

These three thresholds live in `SystemConfiguration`
(`breakdown_streak_minimum_events`, `breakdown_streak_minimum_hours`,
`breakdown_streak_max_gap_hours`) and can be tuned per-plant without a code
change. With the bundled sample dataset, the default thresholds correctly
detect **no qualifying streak** — the failure events present are real, but
none chain tightly enough to meet the 3-event/5-hour bar — which is itself
a meaningful (and correctly conservative) result; loosen the thresholds in
`config_app/data/system_config.json` to see streaks appear in the more
clustered Oct 8 failures.

---

## 12. Testing

### Backend
```bash
cd backend
python manage.py test shifts -v 2
```
27 tests covering:
- **Data cleaning**: missing values, malformed dates, invalid timestamps,
  overnight shifts, implausible gaps, duration mismatches, duplicates.
- **Analytics**: efficiency calculation, distribution percentage sums,
  streak detection (positive case, minimum-threshold case, gap-broken case).
- **Config auto-registration**: unknown activities registered not dropped,
  case-insensitive lookup doesn't create duplicates.
- **API**: response shape, filter correctness (date range, category).

### Frontend
```bash
cd frontend
npm test
```
10 tests covering component rendering (KPI cards, empty states, required
Y-axis labels on the Gantt chart) and dynamic filtering behavior
(chip toggling updates filter state; reset button appears/disappears
based on active filters; filter options render from API data rather than
a fixed list).

---

## 13. Known limitations / next steps

- The Gantt chart is a hand-rolled SVG component rather than a library
  component, since neither Recharts, ECharts, nor D3-via-React ships a
  ready-made Gantt — this was flagged as an explicit exception above.
- Pagination is enabled on the DRF default (`PAGE_SIZE=200`) but the
  custom analytics endpoints return full computed payloads rather than
  paginating, since they're already aggregated and small. For very large
  datasets, consider pushing date-range filtering server-side more
  aggressively (already supported) before requesting `/shift-analysis`.
- Authentication is not implemented — this is an internal-tool MVP. Add
  DRF's `IsAuthenticated` + a session/token scheme before exposing this
  outside a trusted network.
