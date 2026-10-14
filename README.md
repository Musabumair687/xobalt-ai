# Xobalt AI

Xobalt AI is a FastAPI backend and Next.js frontend for lead discovery, enrichment,
scoring, personalized outreach drafts, and human-reviewed email delivery.

## Backend quick start (Windows)

Run the backend from the `backend` directory so its `app` package and `.env` file
resolve consistently:

```powershell
cd backend
python -m venv backend_venv
.\backend_venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

`app.config.Settings` is the sole source for database, Redis, and provider
configuration. It reads `backend/.env` regardless of the current working
directory; environment variables override values from that file. The example
uses local SQLite. Provider credentials are optional for local development and
belong only in `backend/.env` (ignored by Git), never frontend code.
Set `JWT_SECRET_KEY` in `backend/.env` before using authenticated APIs. Generate
a private value with `python -c "import secrets; print(secrets.token_urlsafe(48))"`;
do not commit or share it. The API keeps `/health` and `POST /api/v1/auth/login`
public; the remaining API routes require a bearer access token.
Set `INTEGRATION_ENCRYPTION_KEY` before allowing organizations to save provider
credentials in Settings. Generate one with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
Keep it in the deployment secret manager, use the same key across API and worker
instances, and back it up securely. Losing or changing it without re-encrypting
stored credentials makes those credentials unrecoverable.

Accounts are provisioned by an operator, not through public signup. After
migrations and environment setup, create an organization and its initial owner
interactively:

```powershell
python -m app.commands.provision_user --organization-name "Example" --organization-slug example --email owner@example.com --full-name "Example Owner"
```

Log in by posting JSON containing `email` and `password` to
`/api/v1/auth/login`, then send the returned `access_token` as
`Authorization: Bearer <token>`. Access tokens expire after
`JWT_ACCESS_TOKEN_MINUTES` (30 by default). API data access is constrained to
the authenticated user's active organization. Email sends and campaign
execution require both organization ownership and an explicitly approved
message.

The frontend signs in at `/login` using the provisioned account. It keeps the
bearer token in browser `sessionStorage`, attaches it to API requests, and
redirects back to sign-in if the backend rejects an expired or invalid token.
Signing out or closing the browser tab clears the frontend session.

Alembic owns schema creation and changes. Run `python -m alembic upgrade head`
after installing dependencies and before starting the app. Application startup
does not create or alter tables. For an existing database previously initialized
by SQLAlchemy `create_all`, back it up first and compare its schema with the
baseline migration before running `python -m alembic stamp head`; stamping only
records migration history and does not change the schema. Do not stamp a
database whose schema has not been verified.
Databases stamped with the removed root-level migration history are not
automatically compatible with this baseline; back them up and plan a data/schema
migration rather than stamping them as current.

The root-level `main.py` forwards to the same backend app for compatibility,
but running from `backend` is the supported backend entry point.

Campaign delivery requires the API, Redis, and a separate Celery worker. Start
the worker in another terminal from `backend` after activating the same
environment:

```powershell
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO --pool=solo
```

`--pool=solo` is suitable for local Windows development. Use a supported
multi-process worker pool on Linux in production. `/health` is a liveness
check; `/ready` returns `200` only when the database, Redis broker, and at
least one Celery worker respond. Campaign execution returns a `run_id`; poll
`GET /api/v1/campaigns/executions/{run_id}` for its persisted status and counts.

## Backend tests

From the `backend` directory, activate the environment above and run:

```powershell
python -m pytest -q
```

## Main flow acceptance criteria

The backend's core user journey is complete when a test can discover a lead,
persist its company and contact data, calculate its score, and save an outreach
draft in a pending-approval state. Delivery must happen only after explicit
approval through a configured email provider. Provider errors must be distinct
from valid empty search/enrichment results.

## Phase 1 baseline

Captured on 2026-10-14 before the Phase 1 changes:

- Backend tests: **86 passed, 4 failed**. Failures were the personalization
  workflow missing its persisted `message_id`, plus three scoring expectations
  that differ from current scoring behavior.
- Frontend lint (`npm --prefix frontend run lint -- --quiet`): **27 errors**.
- Frontend production build (`npm --prefix frontend run build`): **passed**.
- Backend startup: **failed** during import because the settings API referenced
  a nonexistent Apollo module/class.

This baseline records known work outside Phase 1; it is not a claim that all
backend or frontend checks currently pass.

Before Phase 1, the working tree already contained changes to the command
notes, dashboard, leads, inbox, sidebar, and untracked frontend feature pages.
Those changes were preserved.

### Phase 1 verification

Checked after the Phase 1 changes on 2026-10-14:

- Backend startup with the documented command: **passed**; `/health` responded
  successfully.
- Settings credential regression test: **1 passed**.
- Full backend suite: **87 passed, 4 failed**. The four failures are the same
  pre-existing personalization persistence and scoring expectation failures
  listed above.
- Settings page ESLint check: **passed**.
- Frontend production build: **passed**.
- Full frontend lint: **24 errors remain**, down from the pre-change 27; these
  are outside the settings page cleanup.
- Provider-key literals were removed from the browser UI and the settings API
  no longer returns masked key fragments. The ignored local `backend/.env` is
  not tracked by Git.

## Phase 2 configuration and database setup

- Canonical settings module: `backend/app/config.py`.
- Canonical application entry point: `backend/app/main.py`, launched from
  `backend` with `python -m uvicorn app.main:app --reload`.
- Canonical migration configuration and revisions: `backend/alembic.ini` and
  `backend/alembic/`.
- Fresh database setup: `python -m alembic upgrade head`.
- Fresh SQLite database smoke test: **passed**; `alembic check` reports no
  schema drift.
- Backend startup against the migrated database: **passed**; `/health` returned
  `200` and `/api/v1/settings/status` returned the five configured integrations.
- Settings regression tests: **2 passed**.
- Full backend suite: **88 passed, 4 failed**. The failures remain the
  personalization workflow's missing persisted `message_id` and three scoring
  expectation mismatches recorded in the Phase 1 baseline. These were resolved
  in Phase 3 below.

## Phase 3 workflow correctness and scoring rules

- The personalization graph now connects validation to message persistence.
  The end-to-end test confirms a database-saved message is returned with its
  `pending_approval` status.
- Industry scoring: a target industry receives full credit, a known non-target
  receives half credit, and missing industry receives no credit.
- Company-size scoring: 10–100 employees (inclusive) receives full credit;
  out-of-range or missing employee counts receive no credit.
- Decision-maker scoring: a recognized decision-maker receives full credit,
  a contact without a title or with a non-decision-maker title receives half
  credit, and no contact receives no credit.
- Focused personalization/scoring tests: **9 passed**.
- Full backend suite: **92 passed**.

## Phase 4 authentication and organization scope

- All API routers except login are protected by bearer JWT authentication;
  `/health` remains a public liveness endpoint.
- Accounts are operator-provisioned using the interactive command above; there
  is no public signup route. Passwords are stored as salted PBKDF2-HMAC-SHA256
  hashes, and access tokens are signed with the required `JWT_SECRET_KEY`.
- Organization-owned lead, company, campaign, message, appointment, and
  conversation operations are scoped to the authenticated user's active
  organization. Unknown or cross-organization resources return `404`.
- Sending/execute routes verify organization ownership and require approval
  before delivery or campaign execution.
- Provider operations require authentication. API request models enforce
  bounds on workflow sizes, appointment ranges, and inbound message lengths.
- Authentication/tenant-isolation regression tests cover missing/invalid
  credentials, own versus foreign organization reads, cross-tenant send/execute
  denials, approval requirements, and tenant-scoped campaign creation.
- Full backend test suite after Phase 4: **94 passed**.

## Phase 5 lead pipeline reliability

- The lead pipeline follows discovery, deduplication, people discovery,
  enrichment, verification, persistence, intelligence, scoring, and draft
  generation. Its response and persisted run record include a status for each
  stage; `/api/v1/hunter/status/{run_id}` returns the safe run details to
  authenticated users in the owning organization.
- Provider selection is explicit. The checked-in defaults and
  `backend/.env.example` select `mock` for discovery, enrichment, verification,
  and email. To use a real provider, set its provider selector and required
  credentials in the backend environment. A missing credential or provider
  request failure is an error, not a successful empty result or an automatic
  switch to mock mode.
- Integration status distinguishes `mock`, `configured`, and
  `not_configured`. `configured` means configuration exists; it does not mean
  the provider has been reached or is healthy. The settings live diagnostic
  probes only providers for which a live check is implemented. No live provider
  calls are part of the automated test suite.
- Mock mode is suitable for local pipeline testing and does not represent
  real provider delivery. Failed stages retain safe error types and stage
  details without persisting provider response bodies or credentials.

## Phase 6 queue, delivery safety, and readiness

- `POST /api/v1/campaigns/{campaign_id}/execute` publishes campaign execution
  to the Redis-backed Celery queue and immediately returns a durable run ID.
  Work executes in the separate worker process, not in the request.
- Campaign runs are recorded in `agent_runs`, including queued/running/retrying,
  completed/failed status, retry count, safe error details, and message outcome
  counts. Queue publication failures mark the run failed and return `503`.
- Email delivery uses the selected configured email provider. The database
  atomically changes an approved message to `sending` before contacting that
  provider; concurrent requests and broker redeliveries cannot claim it twice.
  A provider failure is not automatically resent because a timeout can leave
  delivery uncertain. Messages left in `sending` after a worker crash require
  operator review rather than blind retry.
- Celery retries worker/infrastructure failures up to three times and uses
  late acknowledgement so interrupted tasks can be redelivered. Message
  statuses make those redeliveries safe for already claimed or sent messages.
- `/health` remains a lightweight liveness endpoint. `/ready` checks database,
  Redis broker, and a responding Celery worker and returns `503` with per-service
  results if any required dependency is unavailable.

## Phase 7 frontend API contracts

- Dashboard, analytics, settings, and the company, lead, campaign, message, and
  appointment list endpoints publish explicit response schemas in OpenAPI.
- List endpoints return a consistent envelope:

  ```json
  {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 0,
    "pages": 0
  }
  ```

  Use `page` and `page_size` to request later pages; page size is limited to
  100. Companies support `industry` and `query` filters, and messages support
  `status_filter`.
- Analytics is calculated from records belonging to the authenticated
  organization. Each conversion rate returns its numerator, denominator, and
  definition; integration status means configured, explicitly mocked, or not
  configured and does not claim a successful connectivity probe.
- Editable approval, minimum lead-score, and daily-send guardrails are saved
  per organization and returned by both settings reads and saves.
- Organization owners/admins can select and configure LLM, discovery,
  enrichment, verification, email, and Google Calendar integrations in
  Settings. Credentials are encrypted server-side using
  `INTEGRATION_ENCRYPTION_KEY`, never returned in API responses, and never
  included in frontend source. Environment-provided credentials remain a
  platform fallback. Mock and optional providers are explicit; selecting a
  real provider without its required configuration fails instead of silently
  pretending the integration is live.
- Missing organization-owned records return `404`; invalid request data follows
  FastAPI's `422` validation response.