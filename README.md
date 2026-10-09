# Commerce Control Center — V1

Self-hosted Next.js + FastAPI + PostgreSQL. The Owner has final authority. This release stops at `BRAND_PENDING`.

## Run with Docker

Requires Docker Engine/Desktop with Compose v2. From this directory:

```sh
python3 ops/configure.py
docker compose up -d --build --wait
```

`configure.py` generates independent random database passwords in `.env`, without printing them. It refuses to overwrite an existing file. For manual configuration, copy `.env.example` to `.env` and replace both passwords with different random **alphanumeric** strings (the connection URLs need URL encoding if other characters are used).

Compose starts PostgreSQL, runs Alembic migrations as a one-shot service, then starts the API and frontend. A failed migration blocks application startup. PostgreSQL and the API are private to the Compose network. Only the frontend is bound to `127.0.0.1:3000`.

Open **http://localhost:3000**. Use this exact hostname because `APP_ORIGIN` defaults to it.

## Initial Owner setup

There are no default Docker credentials and no public registration endpoint.

```sh
docker compose exec backend python -m app.cli create-owner --email owner@your-company.com
```

Enter your password at the hidden prompt (minimum 12 characters), repeat it, then sign in at http://localhost:3000/login. Setup closes once an Owner exists. PostgreSQL also enforces one Owner. The password is stored with Argon2, not as plaintext.

If a temporary local preview was provided alongside this checkout, `LOCAL-PREVIEW-ACCESS.txt` contains its separate credentials. That preview uses SQLite and is explicitly marked in the UI. **It is not the Docker/PostgreSQL deployment**, does not validate PostgreSQL locking/permissions, and does not transfer its Owner or data into Docker. Never use its credentials on the VPS.

## Check the deployment

```sh
docker compose ps -a
docker compose logs migrate
curl --fail http://localhost:3000/health
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
docker compose exec db pg_isready -U postgres -d control_center
```

The frontend health route checks its HTTP process. The backend health route queries the database. The PostgreSQL health check uses `pg_isready`. The migration service should exit with code 0; the other three services should be healthy.

## Tests

Fast API/rule tests (SQLite isolation):

```sh
docker compose run --rm backend pytest -q
```

PostgreSQL integration tests, including all API tests against actual PostgreSQL, migrations, application-role permissions, 20-candidate enforcement, completed-record immutability, and simultaneous Owner approvals:

```sh
docker compose --profile test run --build --rm integration-tests
```

Integration tests create randomly named disposable databases prefixed `cc_test_` and drop **only those databases** after each test. They do not erase the application database. PostgreSQL-specific tests are explicitly skipped when `TEST_POSTGRES_URL` is absent; an ordinary SQLite test pass does not claim those tests passed.

Frontend:

```sh
cd frontend
npm ci
npm run typecheck
npm run build
```

For backend testing without Docker, use Python 3.12+, create a virtual environment, install `backend/requirements.lock`, then run `pytest -q` from `backend/`.

See [VERIFICATION.md](VERIFICATION.md) for the checks actually completed in this environment and the remaining blockers.

## What works

- Owner sign-in, session expiry, logout, backend authorization and CSRF/origin checks.
- Dashboard, searchable/filterable projects, creation, detail, Owner-only renaming, audited deletion, unique IDs and timestamps. Deletion hides a project from active views while retaining its research and audit history; it closes pending approvals and revokes project-scoped agent credentials.
- Persisted research runs, up to 20 candidates each, evidence reports, sortable PASS/REVIEW results, and visible rejection reports.
- Owner confirmation of PASS candidates only, with an extra acknowledgement for fixture selections.
- Transactional selection, approval attribution, status change and audit events.
- Owner-controlled research restart, preserving prior results and superseding pending approvals. This also recovers interrupted runs. Approved projects cannot restart in V1.
- Read-only registered agents and settings pages; activity filtering and pagination.
- A project-scoped, capability-limited agent submission API. Submitted statuses/scores are computed by the backend, not accepted from the agent.

## What is synthetic or not configured

The development provider returns five fixed **`.example`** domain candidates: two PASS, one REVIEW, two FAIL. Domain names, scores, historical findings and evidence are synthetic. They are prominently labeled in the results, reports, approval screen, decision and audit details. No live availability, history, backlink, safety, ScamAdviser or pricing service is contacted. Prices remain unknown. A fixture PASS is a **simulated evaluation result**, not a safety finding about a real domain.

`ENABLE_FIXTURES=true` enables this provider; set it to `false` for a live environment. The Domain Research agent is registered but disabled initially; there is no autonomous model loop or live provider configured. No Brand, Social, Shopify, Google Ads, Merchant Center or other agent exists.

There are no payment credentials, purchase/registration/advertising endpoints, payment forms, purchase SDKs, or scraping integrations. Domain selection never purchases or reserves a domain. External source links, if supplied by a future provider, are read-only references.

## Evaluation policy — v1

Hard failures:

- Verified **historical** evidence of gambling, casino, adult content, pornography, drugs, phishing, scams, malware or severe spam.
- Known ScamAdviser score below 75.

Unknown scores, missing verified evidence, any unresolved warning, unverified findings, and any history/backlink/safety check that is not CLEAR require REVIEW. PASS requires CLEAR history/backlinks/safety, both numeric scores, and verified evidence for history, backlinks, safety, ScamAdviser and niche fit. ScamAdviser alone can never produce PASS. REVIEW and FAIL can never be selected through the API.

The recommendation score is `25 × history_clear + 15 × backlinks_clear + 25 × safety_clear + 0.20 × ScamAdviser + 0.15 × niche_fit`, rounded to 0–100. Missing numbers contribute zero. The score is explanatory and **never overrides** a FAIL or REVIEW gate. A high-scoring rejected domain remains rejected. Provider verification flags describe the provenance asserted by that authorized provider; V1 does not independently verify external evidence or infer truth from free text.

## Adding legitimate domain providers later

Implement `backend/app/domains/providers/base.py`'s `DomainProvider` protocol. Input is `project_id`, `market`, `niche`; output is a list of validated `CandidateInput` records. The fixture provider demonstrates the shape. Providers must use authorized APIs/licensed data, obey terms and rate limits, and use bounded timeouts. Preserve source references, observation timestamps and canonical historical categories. Never label an AI-generated guess as verified evidence.

Provider output goes through `ResearchSubmission` validation and `complete_run`; providers cannot grant approvals. Only the fixture is connected to an Owner-triggered runner in V1. No provider credentials are hardcoded. Add server-side environment variables only when integrating an actual provider.

The future agent can use these existing endpoints with its own bearer credential:

- `GET /api/agent/projects/{project_id}/input`
- `POST /api/agent/projects/{project_id}/runs`
- `POST /api/agent/projects/{project_id}/runs/{run_id}/results`

A local operator can issue a project-scoped, 24-hour token using:

```sh
docker compose exec backend python -m app.cli issue-agent-token --project-id PROJECT_UUID
```

This explicitly enables the registered Domain Research interface and prints the token once. No token is issued automatically. Treat it as a secret; do not put it in browser storage. Credentials are hashed in PostgreSQL and support revocation. Agents cannot use Owner endpoints, change security policy, create arbitrary project assignments, or approve critical output. Every route checks the actor and capability on the server.

See [docs/agent-submission.json](docs/agent-submission.json) for the request structure (illustrative only; not actual research).

## Architecture and storage

```text
frontend/src/app/          Next.js pages
frontend/src/components/   Shared shell and UI
frontend/src/lib/          API client and shared types
backend/app/core/          Configuration, sessions and permissions
backend/app/projects/      Projects / CRM
backend/app/domains/       Runs, providers, validation and evaluation
backend/app/approvals/     Owner-only approval transaction
backend/app/audit/         Append-only audit events and reads
backend/app/agents/        Registry and configuration views
backend/app/db/            SQLAlchemy models and sessions
backend/alembic/           Versioned schema and PostgreSQL guards
backend/tests/             Rules, API and PostgreSQL integration tests
ops/                      Initial database role and environment setup
```

The schema contains users, sessions, projects, agents, agent credentials, research runs, domain candidates, evidence, approvals and audit events. JSONB stores structured flexible findings; workflow fields and relationships are relational. IDs are UUID strings. Timestamps are UTC, displayed in the browser's timezone.

A separate database owner runs migrations; `cc_app` runs the application without superuser, role-creation or schema-creation privileges. It can SELECT/INSERT audit events, but cannot UPDATE, DELETE or TRUNCATE them. PostgreSQL triggers also guard audit immutability, completed research, candidate counts and selection integrity. Project-row locks serialize approval and research transitions. The runtime database role can never alter those triggers. A database administrator remains able to administer the database; the audit trail is not cryptographically tamper-proof against that administrator.

All important writes include audit events in their transaction. If approval audit persistence fails, approval rolls back. Request errors and denials are also recorded with generated correlation IDs; errors are logged to stderr if the database itself is unavailable. Authentication payloads and credentials are not logged. There is no audit editing API.

## VPS operation

- Put the loopback-bound frontend behind your HTTPS reverse proxy.
- Set `APP_ORIGIN` to the exact external HTTPS origin and `COOKIE_SECURE=true`.
- Set `ENABLE_FIXTURES=false` unless intentionally demonstrating the system.
- Add login rate limiting at the reverse proxy before exposing the service publicly. V1 has no distributed rate-limit service.
- Keep `.env` private and out of source control. The frontend receives no database credentials or provider secrets.
- Back up the PostgreSQL volume through `pg_dump`; do not treat a running volume copy as a tested backup.

Example backup:

```sh
mkdir -p backups
docker compose exec -T db pg_dump -U postgres -d control_center -Fc > backups/control-center.dump
```

Restore into an empty database with the same role/migration configuration, and test the restored database before replacing production. Database credentials are initialized on the first volume creation; changing `.env` alone does not rotate an existing PostgreSQL password.

`docker compose down` stops services while preserving the volume. Do not use `down -v` unless you intentionally want to destroy stored data.

## Framework references

The implementation follows the [Next.js installation guidance](https://nextjs.org/docs/app/getting-started/installation) and uses Argon2 through `pwdlib`, as illustrated in the [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/). Sessions here are server-side and cookie-based, rather than JWTs.
