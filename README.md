# SLA Monitoring Dashboard

A full-stack application for monitoring service availability, SLA
compliance, failure events, response latency and individual health-check
records.

The application accepts monitoring data through CSV uploads, validates
and cleans the records, normalizes values, detects duplicates, stores
observations in PostgreSQL, calculates overall and service-level
metrics, and exposes APIs consumed by the dashboard.

## Live application and project links

-   **Live dashboard:** https://sla-monitoring-teal.vercel.app/
-   **GitHub repository:** https://github.com/rahulsk05/sla_monitoring
-   **Application demo:** [Watch the application
    demo](https://drive.google.com/file/d/1OXRfXffTK0zqZwJjgD3A9V1dw-PKzCno/view?usp=sharing)
-   **Demo verification and recording date:** 25 November 2026

### Production backend services

  ------------------------------------------------------------------------------------------------------
  Service                 Responsibility          URL
  ----------------------- ----------------------- ------------------------------------------------------
  Upload                  Accepts and processes   https://sla-upload-342201379031.asia-south1.run.app
                          CSV uploads             

  Metrics                 Returns overall and     https://sla-metrics-342201379031.asia-south1.run.app
                          service-level metrics   

  Logs                    Returns filtered and    https://sla-logs-342201379031.asia-south1.run.app
                          paginated monitoring    
                          logs                    
  ------------------------------------------------------------------------------------------------------

The backend services are deployed to Google Cloud Run in `asia-south1`.

------------------------------------------------------------------------

## 1. Architecture

The deployed application consists of a React frontend, three
independently deployed backend HTTP services, and a shared PostgreSQL
database.

``` mermaid
flowchart TD
    U[User / Browser] --> FE[Vercel - React + Vite]
    FE -->|POST CSV| UP[Cloud Run - Upload]
    FE -->|GET metrics| ME[Cloud Run - Metrics]
    FE -->|GET logs| LG[Cloud Run - Logs]
    UP -->|Validate, clean, transform, persist, calculate| DB[(Render PostgreSQL)]
    ME -->|Read precomputed metrics| DB
    LG -->|Read filtered records| DB
```

### What runs where

  -----------------------------------------------------------------------
  Layer                   Technology / hosting    Responsibility
  ----------------------- ----------------------- -----------------------
  Frontend                React, TypeScript,      Dashboard, service
                          Vite, Tailwind CSS v4   metrics view,
                          on Vercel               monitoring logs and CSV
                                                  upload UI

  API communication       Axios                   Calls the three backend
                                                  service URLs

  Frontend server state   TanStack Query          Fetching, caching,
                                                  refreshing and query
                                                  invalidation

  Upload backend          Python function on      Validates, cleans,
                          Google Cloud Run        transforms and
                                                  deduplicates uploaded
                                                  monitoring data;
                                                  persists records and
                                                  recalculates metrics

  Metrics backend         Python function on      Reads precomputed
                          Google Cloud Run        overall and
                                                  service-level metrics

  Logs backend            Python function on      Retrieves monitoring
                          Google Cloud Run        records with filters
                                                  and pagination

  Database                PostgreSQL hosted on    Stores source
                          Render                  monitoring records and
                                                  derived metrics

  Database access         SQLAlchemy 2.x +        ORM and PostgreSQL
                          Psycopg 3               connectivity

  Migrations              Alembic                 Versions and applies
                                                  database schema changes

  Runtime secrets         Google Secret Manager   Supplies the database
                                                  connection URL to Cloud
                                                  Run

  Logs                    Python standard logging Captures application
                          / Cloud Run logs        events and errors
  -----------------------------------------------------------------------

### Why these choices

-   **React + TypeScript:** Provides reusable UI components and type
    checking for API contracts.
-   **Vite:** Provides lightweight local development and production
    build tooling.
-   **Tailwind CSS v4:** Supports consistent styling and responsive
    layouts without adding a separate component framework.
-   **TanStack Query:** Handles API state, loading/error states,
    caching, periodic metrics refresh and cache invalidation after
    uploads. Redux was not needed for this scope.
-   **Axios:** Centralizes HTTP configuration. Separate instances are
    used because the three backend services have different base URLs and
    timeout requirements.
-   **Google Cloud Run:** Hosts the three HTTP functions independently
    while allowing them to share one backend codebase and database
    configuration. Source-based deployment avoids maintaining three
    separate copies of the application.
-   **PostgreSQL:** Fits structured monitoring records, date-range
    queries, filtering, pagination, aggregation and transactional
    writes.
-   **Render PostgreSQL:** Provides a managed PostgreSQL instance
    without requiring database-server administration.
-   **Google Secret Manager:** Keeps database credentials out of source
    code and deployment artifacts.
-   **Precomputed metrics:** Metrics are calculated during upload and
    persisted. The dashboard metrics endpoint reads the stored results
    instead of recalculating over the full logs table on every page
    load.

The database is hosted in Render's Singapore region while Cloud Run
services run in `asia-south1`. This was an acceptable deployment choice
for the assignment; placing database and compute in the same region
would be preferable for lower network latency.

------------------------------------------------------------------------

## 2. Technology stack

### Frontend

  Technology        Purpose
  ----------------- -------------------------------------
  React             UI components
  TypeScript        Static typing
  Vite              Development and build tooling
  Tailwind CSS v4   Styling and responsive layout
  TanStack Query    API fetching, caching and mutations
  Axios             HTTP requests
  Font Awesome      Icons
  Vercel            Frontend hosting

### Backend and database

  -----------------------------------------------------------------------
  Technology                          Purpose
  ----------------------------------- -----------------------------------
  Python                              Backend implementation

  Python 3.10                         Local development environment used
                                      during implementation

  Python 3.12                         Deployed Cloud Run runtime

  Flask / Functions Framework         HTTP function entrypoints

  SQLAlchemy 2.x                      ORM and asynchronous database
                                      access

  Psycopg 3                           PostgreSQL driver

  PostgreSQL                          Persistent storage

  Pandas                              CSV parsing, cleaning,
                                      transformation and analysis

  Alembic                             Database migrations

  Pydantic Settings                   Centralized configuration

  Pytest                              Automated testing

  Google Cloud Run                    Backend hosting

  Google Secret Manager               Database secret management

  Render                              Managed PostgreSQL hosting
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 3. CSV ingestion, cleaning and transformation

The application is designed to process compatible monitoring-data CSV
uploads. It is not tied to one specific CSV file or sample dataset.
Uploaded files must follow the monitoring record structure expected by
the application.

The expected source fields represent:

-   Service identifier and name
-   Observation timestamp
-   HTTP status code
-   Response latency and its unit
-   Monitoring agent
-   Region

The upload endpoint accepts a file through `multipart/form-data`, using
the form field name `file`.

### 3.1 File and schema validation

Before processing:

1.  The upload handler extracts the file from the request.
2.  Base64-encoded request bodies are decoded when necessary.
3.  The actual decoded file size is checked.
4.  Empty or invalid upload content is rejected.
5.  The CSV structure and expected columns are validated.

The maximum upload size is **5 MB** (`5 * 1024 * 1024` bytes). An
oversized upload is rejected with HTTP 413 before CSV parsing or
database operations.

A file-level schema problem rejects the upload. Individual records with
invalid mandatory fields are handled separately so that valid records
can still be processed.

The mandatory record fields are service identifier, service name,
timestamp and status code. Optional or quality-sensitive fields such as
latency are handled according to the normalization rules below.

### 3.2 Chunk-based processing

Pandas is used to read and process CSV data in chunks of **5,000 rows**.

Chunk-based processing avoids loading the entire file into one large
DataFrame and keeps memory usage more predictable.

Duplicate tracking is maintained across chunks, not only within the
current chunk. This matters because identical records may appear in
different parts of the same uploaded file.

### 3.3 Data cleaning and normalization

The cleaning workflow applies the following rules.

  -----------------------------------------------------------------------
  Data area                           Cleaning / transformation rule
  ----------------------------------- -----------------------------------
  Mandatory fields                    Reject records with missing or
                                      invalid mandatory values

  Timestamps                          Support ISO timestamps ending in
                                      `Z`, ISO timestamps with timezone
                                      offsets and Unix epoch timestamps
                                      in seconds

  Timezone                            Normalize accepted timestamps to
                                      UTC

  Database timestamp                  Store as PostgreSQL `TIMESTAMPTZ`

  Latency in seconds                  Convert to milliseconds

  Latency in milliseconds             Keep unchanged

  Missing latency                     Store as `NULL`

  Invalid latency                     Store as `NULL`

  Negative latency                    Store as `NULL`

  HTTP 2xx                            Classify as successful

  HTTP 5xx                            Classify as failed

  Other valid statuses                Retain as unknown; exclude from
                                      availability calculations
  -----------------------------------------------------------------------

An invalid latency value does not automatically invalidate an otherwise
valid status observation. The record can still contribute to
availability and remain visible in monitoring logs, while being excluded
from latency statistics.

Unknown status observations are also retained for investigation. They
are not silently classified as successful or failed.

### 3.4 Duplicate detection

The application uses a deterministic SHA-256 fingerprint generated from
all original source fields in a monitoring record, before normalization.

Duplicate protection is applied at two levels:

1.  During the upload, to detect duplicate records across CSV chunks.
2.  In PostgreSQL, to prevent records already stored by earlier uploads
    from being inserted again.

The database enforces uniqueness on `record_hash`. Inserts use
PostgreSQL `ON CONFLICT DO NOTHING`.

The application deliberately does **not** deduplicate using only service
identifier and timestamp. Different monitoring agents can produce
distinct observations for the same service at the same timestamp; those
observations must be preserved.

### 3.5 Processing outcomes

The cleaning workflow produces a structured summary using
`CleaningSummary` and `CleaningResult` dataclasses.

The upload response reports:

-   Total source rows
-   Accepted rows
-   Partially accepted rows
-   Rejected rows
-   Duplicate rows
-   Newly inserted rows
-   Number of services processed
-   Upload ID

The outcomes have the following meaning:

-   **Accepted:** Mandatory values and relevant record fields are valid.
-   **Partially accepted:** The observation is valid, but a
    non-mandatory value such as latency is missing or invalid and is
    stored as `NULL`.
-   **Rejected:** A mandatory field is missing or invalid.
-   **Duplicate:** The same complete source record has already appeared
    in the upload or database.
-   **Inserted:** A new unique monitoring record was actually persisted.

The application uses the database insert result with `RETURNING` to
count records actually inserted, rather than relying on a driver
`rowcount` value that may not be reliable for this operation.

------------------------------------------------------------------------

## 4. Analysis and metric calculations

After cleaning and normalization, valid monitoring observations are
stored in PostgreSQL. The upload workflow then calculates overall and
service-level metrics from the accumulated monitoring history.

The database uses three application tables:

1.  `monitoring_logs` --- source monitoring observations.
2.  `overall_metrics` --- one consolidated overall metrics record.
3.  `service_metrics` --- one precomputed metrics record per service.

`monitoring_logs` is the source of truth. The metrics tables contain
derived data that can be recalculated from the source records.

### 4.1 Availability

The availability calculation is:

``` text
Availability =
    Successful checks
    ----------------------------------------- × 100
    Successful checks + Failed checks
```

Assumptions:

-   HTTP 2xx observations are successful.
-   HTTP 5xx observations are failed.
-   Unknown/other statuses are excluded from the denominator.
-   Overall availability is calculated from combined successful and
    failed observations across all services. It is not the average of
    individual service percentages.
-   Total health checks includes accepted observations with unknown
    statuses.
-   Missing latency does not remove an otherwise valid status
    observation from availability.

This is an observation-based availability calculation. The application
does not fabricate missing checks or infer downtime solely from gaps in
timestamps.

### 4.2 SLA evaluation

The SLA threshold is fixed at **99.9%**.

``` text
meets_sla = availability_percentage >= 99.9
```

A service is marked as meeting SLA when its availability is greater than
or equal to the threshold. The threshold is not configurable through the
frontend or API.

### 4.3 Latency analysis

Average and P95 latency are calculated separately for each service.

Rules:

-   Only successful 2xx observations with valid, non-negative latency
    are included.
-   Failed and unknown observations are excluded.
-   All latency values are normalized to milliseconds.
-   P95 uses Pandas `quantile(0.95)` with its default linear
    interpolation.
-   If no valid latency samples exist for a service, average and P95 are
    `NULL`.
-   `latency_sample_count` records how many observations contributed to
    the latency statistics.

No overall average or P95 latency is calculated for the dashboard.

### 4.4 Failure-event calculation

A failure event is a sequence of consecutive 5xx observations for one
service.

-   The first 5xx observation starts an event.
-   Consecutive 5xx observations belong to the same event.
-   A 2xx observation ends the active event.
-   A later 5xx observation starts a new event.
-   Unknown statuses neither start nor end an event.
-   If an event is still active at the end of the available history, it
    is treated as ongoing through the last available observation for
    that service.

All monitoring agents are treated as one consolidated stream per
service. Agent information is preserved in the logs for traceability and
filtering, but agent-level availability is not calculated.

Observations are sorted deterministically for failure-event
calculations. When timestamps are identical, `record_hash` is used as a
tie-breaker. The logs API uses `observed_at DESC, id DESC` for stable
pagination.

Overall failure-event count is the sum of service-level failure-event
counts. Overall longest failure duration is the maximum among the
services.

### 4.5 Dashboard statistics selected

The overall dashboard contains six summary KPIs:

1.  Overall availability
2.  Total health checks
3.  Failed checks
4.  Failure events
5.  Longest failure duration
6.  Services below SLA

The service-level metrics view provides:

-   Service name
-   Total health checks
-   Availability
-   Average latency
-   P95 latency
-   Failed checks
-   Failure events
-   Longest failure duration
-   SLA status

The monitoring logs table provides the underlying observations for
investigation, with date, service and agent filtering and pagination.

These statistics were selected to cover availability, workload,
reliability, incidents, latency and SLA compliance without adding
unnecessary metrics. Data-quality outcomes are shown as part of upload
feedback rather than as dashboard KPIs.

------------------------------------------------------------------------

## 5. Database design

### `monitoring_logs`

Stores accepted and unique monitoring observations:

-   `id`
-   `record_hash`
-   `service_id`
-   `service_name`
-   `observed_at`
-   `status_code`
-   `latency_ms`
-   `agent`
-   `region`
-   `upload_id`
-   `created_at`

`record_hash` has a unique constraint. Indexes support timestamp-based
queries and service-plus-timestamp queries.

### `overall_metrics`

Stores:

-   Total checks
-   Availability-eligible checks
-   Successful checks
-   Failed checks
-   Availability percentage
-   Services below SLA
-   Total failure events
-   Longest failure duration
-   SLA threshold
-   Calculation and update timestamps

The table is designed to contain one logical overall metrics row.

### `service_metrics`

Stores one record per service:

-   Service ID and name
-   Total checks
-   Availability-eligible checks
-   Successful and failed checks
-   Availability percentage
-   Average latency
-   P95 latency
-   Latency sample count
-   Failure-event count
-   Longest failure duration
-   SLA status
-   Calculation and update timestamps

`service_id` is the primary key.

### Why PostgreSQL

PostgreSQL was selected because the application requires structured
records, date-range filtering, service-based filtering, stable
pagination, aggregation and analytical calculations.

It also allows the monitoring records and derived metric updates from
one upload to be committed atomically in a single transaction.

Alembic maintains its migration metadata table (`alembic_version`). This
is migration infrastructure, not an additional application data table.

------------------------------------------------------------------------

## 6. Backend APIs

The backend is exposed through three independent Cloud Run services.

  Operation          Method   Service
  ------------------ -------- -----------------
  Upload CSV         POST     Upload service
  Retrieve metrics   GET      Metrics service
  Retrieve logs      GET      Logs service

### Metrics API

The metrics endpoint reads the precomputed `overall_metrics` and
`service_metrics` records. It does not recalculate metrics on each
dashboard request.

The response provides overall and service-level metrics.

### Logs API

The logs endpoint supports:

  Parameter      Purpose
  -------------- ----------------------------
  `page`         1-based page number
  `date`         One UTC calendar date
  `start_date`   Start date of a range
  `end_date`     End date of a range
  `service_id`   Filter by service
  `agent`        Filter by monitoring agent

Examples:

``` http
GET /logs
GET /logs?page=2
GET /logs?date=2026-11-24
GET /logs?start_date=2026-11-20&end_date=2026-11-24
GET /logs?service_id=svc-auth
GET /logs?date=2026-11-24&service_id=svc-auth&agent=agent-1
```

Pagination behaviour:

-   Page size is fixed at 50 records.
-   The backend returns pagination metadata: `page`, `page_size`,
    `total_records` and `total_pages`.
-   Results are sorted by `observed_at DESC, id DESC`.
-   Count and data queries use the same filters.

Date behaviour:

-   Date filtering uses UTC calendar-day boundaries.
-   Date ranges include both supplied calendar dates.
-   The database query uses a half-open interval: start inclusive,
    next-day/end boundary exclusive.
-   The frontend displays timestamps in the browser's local timezone,
    while the backend interprets date filters as UTC.

Invalid page numbers, date formats, incomplete ranges, conflicting date
filters and unsupported query parameters return HTTP 400.

------------------------------------------------------------------------

## 7. Reliability, transactions and error handling

### Atomic upload transaction

Each upload is treated as one database transaction:

1.  Validate and clean the CSV.
2.  Begin the database transaction.
3.  Insert new monitoring records.
4.  Retrieve the monitoring history required for calculations.
5.  Calculate service-level metrics.
6.  Upsert service-level metrics.
7.  Calculate overall metrics.
8.  Upsert overall metrics.
9.  Commit the transaction.

If a database write or metric persistence operation fails, the
transaction is rolled back. Newly inserted monitoring records and metric
changes from that upload are not committed, while previously committed
data remains unchanged.

The upload workflow owns transaction coordination. Repositories do not
commit independently.

### Duplicate safety

The unique constraint on `record_hash`, combined with PostgreSQL
`ON CONFLICT DO NOTHING`, makes repeated uploads safe from duplicate
insertion. A duplicate is a normal processing outcome, not a database
failure.

### Error handling

Error handling is centralized. Application errors return controlled HTTP
responses with an error message and code. Unexpected errors return a
generic response rather than exposing internal exception details.

  Error                                  HTTP status
  ------------------------------------ -------------
  Invalid CSV or query parameters                400
  CSV exceeds 5 MB                               413
  Unexpected server/database failure             500

Unexpected exceptions are logged for debugging.

### Logging

The shared Python logger writes timestamped messages to standard output
so the hosting platform can collect them. Important events include CSV
processing, inserted and duplicate counts, metrics retrieval, database
failures and request errors.

The upload ID is associated with monitoring records to help trace
records back to an upload.

### Database connection management

The backend uses SQLAlchemy's asynchronous engine and `AsyncSession`.
The deployed configuration uses `NullPool` and `pool_pre_ping=True`. A
database session is created for request handling and closed after the
operation. `NullPool` avoids retaining application-level pooled
connections across the handler execution model.

------------------------------------------------------------------------

## 8. Frontend behaviour

The frontend includes:

-   Dashboard header with title, last-updated timestamp and refresh
    action.
-   Six overall metric cards in a collapsible section.
-   Service-level metrics modal.
-   Monitoring logs table.
-   CSV upload modal.
-   Dashboard footer.

The layout uses the available viewport height and keeps scrolling within
the logs area rather than making the entire dashboard page scroll.

### Data fetching and refresh

-   TanStack Query manages API server state.
-   Metrics refresh automatically every 60 seconds.
-   Logs are not automatically polled; the user can refresh them
    manually.
-   Pagination and filter values are part of the logs query key.
-   After a successful CSV upload, metrics and logs queries are
    invalidated so the dashboard can refresh without a full page reload.

### CSV upload UI

The upload modal supports file selection/drag-and-drop and displays
validation errors, upload progress, success and failure states.

The frontend validates the `.csv` extension, non-empty files and the 5
MB maximum. The backend independently enforces its own validation;
frontend checks are not treated as a security boundary.

------------------------------------------------------------------------

## 9. Local development setup

### Prerequisites

-   Git
-   Node.js and npm
-   Python (local backend development was carried out with Python 3.10)
-   PostgreSQL database access
-   pgAdmin (optional, for database inspection)
-   Google Cloud CLI only if redeploying backend services

Clone the repository:

``` bash
git clone https://github.com/rahulsk05/sla_monitoring.git
cd sla_monitoring
```

### 9.1 Frontend setup

Move into the frontend directory and install dependencies:

``` bash
cd frontend
npm install
```

Create `frontend/.env`:

``` env
VITE_METRICS_API_URL=https://sla-metrics-342201379031.asia-south1.run.app
VITE_LOGS_API_URL=https://sla-logs-342201379031.asia-south1.run.app
VITE_UPLOAD_API_URL=https://sla-upload-342201379031.asia-south1.run.app
```

Start the Vite development server:

``` bash
npm run dev
```

The default development address is:

``` text
http://localhost:5173
```

Build the frontend:

``` bash
npm run build
```

The production assets are generated in `frontend/dist`.

### 9.2 Backend setup

Open a separate terminal and move into the backend directory:

``` bash
cd backend
```

Create a virtual environment.

**Windows CMD:**

``` cmd
python -m venv venv
venv\Scripts\activate
```

**PowerShell:**

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade pip and install the backend dependencies:

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a local `.env` file using `.env.example` as the reference.
Configure the database connection URL:

``` env
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE_NAME?sslmode=require
```

Use your own PostgreSQL credentials. Do not commit `.env` or share the
connection URL.

The backend configuration is managed through Pydantic Settings. Keep
local configuration in `.env`; production configuration is supplied
through Google Cloud Secret Manager and the Cloud Run service
environment.

### 9.3 Database migrations

Check the current Alembic revision:

``` bash
alembic current
```

Apply migrations:

``` bash
alembic upgrade head
```

When changing database models, generate a migration:

``` bash
alembic revision --autogenerate -m "describe database changes"
```

Review the generated migration before applying it with
`alembic upgrade head`.

Do not rely on SQLAlchemy `create_all()` as the production
schema-management mechanism. Use Alembic migrations.

### 9.4 Run the backend locally

The backend exposes three Google Cloud function entrypoints:

-   `upload_csv`
-   `get_metrics`
-   `get_logs`

For local HTTP testing, prepare a small staging directory containing the
application source, the Google Cloud runtime dependencies and the
function entrypoint file. From the backend project root:

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path "deployment/google_cloud"
Copy-Item -Path "src" -Destination "deployment/google_cloud/src" -Recurse -Force
Copy-Item "requirements-gcp.txt" "deployment/google_cloud/requirements.txt" -Force
```

**Linux/macOS:**

```bash
mkdir -p deployment/google_cloud
cp -R src deployment/google_cloud/
cp requirements-gcp.txt deployment/google_cloud/requirements.txt
```

Create `deployment/google_cloud/main.py` with:

```python
from src.entrypoints.google_cloud.upload_function import upload_csv
from src.entrypoints.google_cloud.metrics_function import get_metrics
from src.entrypoints.google_cloud.logs_function import get_logs
```

Install the runtime dependencies:

```bash
pip install -r deployment/google_cloud/requirements.txt
```

Run the selected function from the backend project root. This keeps the
backend `.env` file in the current working directory while the
Functions Framework loads the staging entrypoint:

```bash
functions-framework --target=upload_csv --source=deployment/google_cloud/main.py --port=8080
```

To run the metrics function instead:

```bash
functions-framework --target=get_metrics --source=deployment/google_cloud/main.py --port=8080
```

To run the logs function instead:

```bash
functions-framework --target=get_logs --source=deployment/google_cloud/main.py --port=8080
```

Run one target at a time. The selected function is available locally on
port `8080`. Ensure the backend `.env` contains a reachable PostgreSQL
URL and that database migrations have been applied before sending
requests. The generated deployment directory is excluded from Git and
can be recreated whenever required.

### 9.5 Run backend tests

From the backend directory with the virtual environment activated:

``` bash
pytest
```

The latest recorded backend test run reported **115 tests passed**. The
tests cover repository, service and handler behaviour, including upload
processing, duplicate handling, metrics calculations, logs filtering,
pagination, validation and error handling.

------------------------------------------------------------------------

## 10. Deployment

The production deployment uses Vercel for the frontend, Google Cloud Run
for the three backend services, Render for PostgreSQL and Google Secret
Manager for the database connection secret.

### 10.1 Frontend deployment --- Vercel

The GitHub repository is connected to Vercel. The frontend is deployed
as a separate Vite project.

  Vercel setting     Value
  ------------------ -----------------
  Framework preset   Vite
  Root directory     `frontend`
  Install command    `npm install`
  Build command      `npm run build`
  Output directory   `dist`

The following environment variables are configured in Vercel for
Production and Preview:

``` env
VITE_METRICS_API_URL=https://sla-metrics-342201379031.asia-south1.run.app
VITE_LOGS_API_URL=https://sla-logs-342201379031.asia-south1.run.app
VITE_UPLOAD_API_URL=https://sla-upload-342201379031.asia-south1.run.app
```

Vercel retrieves the repository, installs frontend dependencies, runs
the production build and publishes the `dist` directory.

**Redeploying the frontend**

Push changes to the connected GitHub deployment branch. Vercel
automatically starts a new deployment. If environment variables change,
trigger a new deployment so the Vite build includes the updated values.

### 10.2 Backend deployment --- Google Cloud Run

The backend uses one Python codebase, deployed as three independent
Cloud Run services. Each service uses the same source and dependencies;
the selected function entrypoint determines the operation exposed by
that service.

  Cloud Run service   Function target   Responsibility
  ------------------- ----------------- ----------------------------------
  `sla-upload`        `upload_csv`      CSV ingestion and metric updates
  `sla-metrics`       `get_metrics`     Read overall and service metrics
  `sla-logs`          `get_logs`        Read filtered and paginated logs

Deployment region: `asia-south1`.

The deployment uses source-based deployment through the Google Cloud
CLI. Google Cloud Build builds the source, and Artifact Registry stores
the resulting image.

#### Prepare the deployment source

The deployment staging directory is generated locally and excluded from
Git. From the backend project root:

**Windows PowerShell:**

``` powershell
New-Item -ItemType Directory -Force -Path "deployment/google_cloud"
Copy-Item -Path "src" -Destination "deployment/google_cloud/src" -Recurse -Force
Copy-Item "requirements-gcp.txt" "deployment/google_cloud/requirements.txt" -Force
```

**Linux/macOS:**

``` bash
mkdir -p deployment/google_cloud
cp -R src deployment/google_cloud/
cp requirements-gcp.txt deployment/google_cloud/requirements.txt
```

Create `deployment/google_cloud/main.py`:

``` python
from src.entrypoints.google_cloud.upload_function import upload_csv
from src.entrypoints.google_cloud.metrics_function import get_metrics
from src.entrypoints.google_cloud.logs_function import get_logs
```

The staging directory should contain:

``` text
deployment/google_cloud/
├── main.py
├── requirements.txt
└── src/
    ├── core/
    ├── database/
    ├── models/
    ├── repositories/
    ├── services/
    └── entrypoints/
        └── google_cloud/
            ├── upload_function.py
            ├── metrics_function.py
            └── logs_function.py
```

The deployment-specific requirements file includes the Functions
Framework, Flask, SQLAlchemy, Pandas, Psycopg 3 and other runtime
dependencies.

Do not include local virtual environments, `__pycache__`, tests unless
needed at runtime, `.env` files, database credentials or Git metadata.

The generated directory is excluded from Git using:

``` gitignore
/backend/deployment/google_cloud/
```

#### Configure Google Cloud

Install the Google Cloud CLI and authenticate:

``` bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region asia-south1
```

Enable the required APIs:

``` bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
```

Create the runtime service account:

``` bash
gcloud iam service-accounts create sla-functions-runtime --display-name="SLA Functions Runtime"
```

The service account email follows this format:

``` text
sla-functions-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### Configure the database secret

The PostgreSQL connection URL is stored in Google Secret Manager instead
of being hardcoded or committed to Git.

Create the secret:

``` bash
gcloud secrets create DATABASE_URL --replication-policy="automatic"
```

The connection URL uses the Psycopg 3 SQLAlchemy dialect:

``` text
postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE_NAME?sslmode=require
```

Save the complete URL in a temporary local file named
`database-url.txt`, then add it as a secret version:

``` bash
gcloud secrets versions add DATABASE_URL --data-file="database-url.txt"
```

Grant the Cloud Run runtime service account access:

``` bash
gcloud secrets add-iam-policy-binding DATABASE_URL --member="serviceAccount:sla-functions-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

After confirming that the secret version was created, delete the
temporary file:

``` cmd
del database-url.txt
```

Do not print the secret value in logs or commit the temporary file.

#### Deploy the three services

Run these commands from `backend/deployment/google_cloud`. Replace the
project ID and secret version with the values for your Google Cloud
project.

Upload:

``` bash
gcloud run deploy sla-upload --source . --function upload_csv --base-image python312 --region asia-south1 --service-account sla-functions-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com --set-secrets="DATABASE_URL=DATABASE_URL:SECRET_VERSION" --allow-unauthenticated
```

Metrics:

``` bash
gcloud run deploy sla-metrics --source . --function get_metrics --base-image python312 --region asia-south1 --service-account sla-functions-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com --set-secrets="DATABASE_URL=DATABASE_URL:SECRET_VERSION" --allow-unauthenticated
```

Logs:

``` bash
gcloud run deploy sla-logs --source . --function get_logs --base-image python312 --region asia-south1 --service-account sla-functions-runtime@YOUR_PROJECT_ID.iam.gserviceaccount.com --set-secrets="DATABASE_URL=DATABASE_URL:SECRET_VERSION" --allow-unauthenticated
```

Include any other required application environment variables when
deploying. The commands above show the deployment pattern and secret
mapping; use the current project ID, service account and secret version.

#### CORS configuration

The backend reads allowed browser origins from `CORS_ALLOWED_ORIGINS`.
The deployed configuration allows both local development and the
production Vercel domain:

``` text
http://localhost:5173,https://sla-monitoring-teal.vercel.app
```

This setting is applied to all three Cloud Run services. If the frontend
domain changes, update the CORS allowlist on all three services.

When updating a comma-separated value with `gcloud`, use a custom
delimiter so the comma inside the value is not interpreted as a
separator between environment-variable assignments. The deployment used
`--update-env-vars` to preserve existing settings, including the
database secret mapping.

#### Redeploying backend changes

1.  Apply any required database migration before deploying code that
    depends on the changed schema.
2.  Recreate the `deployment/google_cloud` staging directory from the
    current backend source.
3.  Copy the current `requirements-gcp.txt` as the staging
    `requirements.txt`.
4.  Verify `main.py` imports the current function entrypoints.
5.  Authenticate with the correct Google Cloud project.
6.  Run the relevant `gcloud run deploy` command from the staging
    directory.
7.  Verify the new Cloud Run revision, service URL and traffic
    allocation.
8.  Check Cloud Run logs and test the corresponding API operation.

The services are deployed independently, so deploy each service whose
source or runtime behaviour needs to change.

### 10.3 Database deployment and migrations

The hosted PostgreSQL database is provisioned on Render. Cloud Run
connects to it using the external TLS-enabled connection URL stored in
Secret Manager.

Before deploying application code that depends on a schema change,
configure the correct `DATABASE_URL` and apply the Alembic migration:

``` bash
alembic upgrade head
```

Verify the current migration:

``` bash
alembic current
```

Migrations should be applied deliberately; do not run schema creation or
migration commands on every API request.

### 10.4 Recorded deployment status

The deployment reports record successful production deployment of the
frontend and all three backend services.

  Service         Recorded revision           Traffic
  --------------- ------------------------- ---------
  `sla-upload`    `sla-upload-00005-xp7`         100%
  `sla-metrics`   `sla-metrics-00007-svg`        100%
  `sla-logs`      `sla-logs-00004-sn4`           100%

The frontend is available at the Vercel production URL. The three
backend services are available at their Cloud Run URLs listed at the
beginning of this README.

------------------------------------------------------------------------

## 11. Testing and verification

### Backend tests

The backend test suite covers repository, service and handler behaviour,
including:

-   Bulk inserts and duplicate handling.
-   Duplicate detection across chunks and repeated uploads.
-   Monitoring history retrieval.
-   Metrics retrieval and calculations.
-   Failure-event and latency calculations.
-   Pagination and offset calculations.
-   Date and date-range filtering.
-   Service and agent filters, including combined filters.
-   Deterministic ordering.
-   Invalid query parameters and error responses.
-   Handler session lifecycle.

The latest recorded test run reported **115 tests passed**. This is the
reported automated test result and should not be interpreted as proof
that every possible production end-to-end scenario has been exercised.

### Upload verification

Upload testing verified that valid records could be inserted and that
re-uploading the same source data did not create duplicate monitoring
records.

The implementation also corrected inserted-row counting by using
PostgreSQL `RETURNING` rather than relying on the execution result's
`rowcount`.

### Deployment verification

The deployment reports record that:

-   The frontend was successfully deployed to Vercel.
-   The three backend services were successfully deployed to Cloud Run
    in `asia-south1`.
-   The production Vercel origin was added to the CORS allowlist of all
    three backend services while retaining localhost access.
-   The recorded Cloud Run revisions were serving 100% of traffic.

The application demo linked above was **verified and recorded on 25
November 2026**.

For future code changes, verify the live upload, metrics and logs flows
rather than relying only on deployment status.

------------------------------------------------------------------------

## 12. Assumptions and scope decisions

  -----------------------------------------------------------------------
  Area                    Decision                Reason
  ----------------------- ----------------------- -----------------------
  Input files             Accept CSV files that   Supports different
                          follow the              compatible uploads
                          application's expected  without depending on
                          monitoring-record       one sample file
                          schema                  

  File schema             Missing expected        The application needs a
                          columns reject the      consistent set of
                          upload                  fields to interpret
                                                  records

  Invalid mandatory       Reject the affected     Preserves usable data
  fields                  records while           from a partially valid
                          continuing with valid   file
                          records                 

  Invalid latency         Normalize to `NULL`     Status information
                          without rejecting an    remains useful for
                          otherwise valid         availability
                          observation             

  Timestamp               Normalize to UTC        Handles mixed timestamp
                                                  formats consistently

  Duplicate identity      Hash all original       Preserves distinct
                          source fields           observations sharing a
                                                  service and timestamp

  SLA                     Fixed at 99.9%          No configurable SLA
                                                  feature is required

  Availability            Successful 2xx divided  Uses observed
                          by successful plus      health-check outcomes
                          failed 5xx              

  Unknown statuses        Retain in logs, exclude Avoids treating
                          from availability       unclassified responses
                                                  as success or failure

  Missing checks          No synthetic records or A missing row does not
                          inferred downtime       prove an outage

  Agents                  Consolidated per        Preserves traceability
                          service; agent retained without agent-specific
                          in logs                 availability metrics

  Latency statistics      Successful 2xx checks   Keeps response-time
                          with valid latency only statistics focused on
                                                  successful service
                                                  responses

  P95                     Pandas `quantile(0.95)` Provides a standard,
                          default linear          reproducible percentile
                          interpolation           calculation

  Failure event           Consecutive 5xx         Provides a simple
                          observations form an    incident grouping
                          event; 2xx ends it      without an
                                                  incident-management
                                                  subsystem

  Ongoing failure         Duration extends to the No recovery observation
                          last available          exists in the available
                          observation             history

  Date filtering          UTC calendar dates;     Keeps backend filtering
                          frontend displays local consistent
                          timestamps              

  Pagination              50 records per page,    Keeps responses bounded
                          deterministic ordering  and page boundaries
                                                  stable

  Upload behaviour        Append new unique       Supports overlapping
                          observations; skip      uploads without
                          existing fingerprints   duplicating history

  Upload consistency      One PostgreSQL          Prevents partial
                          transaction per upload  monitoring and metric
                                                  writes

  Dashboard KPIs          Six overall KPIs plus   Covers availability,
                          service-level metrics   failures, incidents,
                                                  latency and SLA
                                                  compliance

  Data quality            Show processing         Data quality is
                          outcomes after upload,  important during
                          not as dashboard KPIs   ingestion but is not a
                                                  primary service-health
                                                  KPI

  Authentication          Not implemented         Outside the assignment
                                                  scope
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 13. What I would improve with more time

1.  **End-to-end and failure-injection tests:** Exercise all three
    deployed services against the hosted database, including deliberate
    failures during inserts and metric updates to verify rollback.
2.  **Larger upload handling:** The current upload is limited to 5 MB
    and uses a synchronous request. For substantially larger files, use
    object storage and asynchronous processing with explicit progress
    and completion status.
3.  **Database and compute region alignment:** Host PostgreSQL closer to
    Cloud Run to reduce cross-region database latency.
4.  **Scalable metric recalculation:** The current upload flow
    recalculates metrics from accumulated monitoring history. For a much
    larger history, consider incremental aggregates or a carefully
    designed background calculation strategy while preserving percentile
    and failure-event semantics.
5.  **Observability:** Add request correlation IDs, dashboards for
    service errors and latency, and alerts for failed uploads or
    database connectivity issues.
6.  **API contract documentation:** Publish an OpenAPI specification and
    example request/response payloads for all three services.
7.  **Operational security:** Add authentication/authorization, stricter
    upload validation and rate limiting if the application is used
    beyond this assignment.
8.  **Historical trends:** Add time-series availability and latency
    charts if historical trend analysis becomes a product requirement.
9.  **Database lifecycle:** Define retention, backup and recovery
    expectations for a long-running deployment.
10. **Deployment automation:** Add a lightweight CI workflow for tests
    and repeatable deployments once the core functionality is stable.

These are future improvements, not requirements for the current
assignment.

------------------------------------------------------------------------

## 14. Repository structure

``` text
sla_monitoring/
├── backend/
│   ├── alembic/
│   ├── src/
│   │   ├── core/
│   │   ├── database/
│   │   ├── entrypoints/
│   │   │   └── google_cloud/
│   │   ├── handlers/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── .env.example
│   ├── alembic.ini
│   ├── requirements.txt
│   └── requirements-gcp.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── features/
│   │   │   ├── dashboard/
│   │   │   ├── monitoring-logs/
│   │   │   └── csv-upload/
│   │   ├── lib/
│   │   └── styles/
│   ├── package.json
│   └── vite.config.ts
│
└── .gitignore
```

The generated `backend/deployment/google_cloud/` directory is
intentionally excluded from Git and recreated locally when deploying.

------------------------------------------------------------------------

## 15. Security and operational notes

-   Never commit `.env`, database URLs, passwords, secret files or
    service-account credentials.
-   Frontend `VITE_*` variables are public API URLs, not secrets.
-   Database credentials are supplied to Cloud Run through Google Secret
    Manager.
-   CORS should allow only intended frontend origins.
-   CORS is not a substitute for authentication or authorization.
-   Apply Alembic migrations deliberately before deploying code that
    depends on schema changes.
-   Review the selected database provider's backup, retention and
    recovery options before using the application for important
    production data.
-   Live URLs, provider plans and free-tier limits may change; verify
    current provider settings before making operational changes.

------------------------------------------------------------------------

## 16. References

-   [GitHub repository](https://github.com/rahulsk05/sla_monitoring)
-   [Live application](https://sla-monitoring-teal.vercel.app/)
-   [Application demo video --- verified and recorded 25 November
    2026](https://drive.google.com/file/d/1OXRfXffTK0zqZwJjgD3A9V1dw-PKzCno/view?usp=sharing)
-   [Google Cloud Run function deployment
    documentation](https://docs.cloud.google.com/run/docs/deploy-functions)
