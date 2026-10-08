# Verification — 8 October 2026

The V1 implementation is complete. Full Docker/PostgreSQL deployment verification remains blocked on this machine.

| Check | Result |
| --- | --- |
| Automated rules and API tests | **34 passed** |
| PostgreSQL-specific integrity/concurrency tests | **4 explicitly skipped** — no usable PostgreSQL runtime |
| Next.js production build | **Passed** |
| TypeScript typecheck | **Passed** |
| Alembic upgrades on SQLite preview | **Passed**, revision `0002_guards` |
| PostgreSQL migration SQL generation | **Passed offline**; not equivalent to execution |
| Compose YAML parsing and private DB/API port assertions | **Passed**; Docker CLI validation unavailable |
| Frontend HTTP health | **200**, local production-build preview |
| Backend HTTP/database health | **200**, connected to SQLite preview |
| Browser Owner login, project creation, fixture research, evidence report | **Passed** |
| Browser REVIEW selection disabled and explicit demo acknowledgement | **Passed** |
| Browser Owner approval → BRAND_PENDING and audit event | **Passed** |
| Browser Agents/Settings and desktop/responsive navigation | **Passed** |
| Browser console errors/warnings during successful walkthrough | None observed |
| Docker Compose stack startup | **Blocked**: `docker: command not found` |
| Native temporary PostgreSQL 17.10 startup | **Blocked**: sandbox denies `shmget` (`Operation not permitted`) |
| PostgreSQL migration execution and health | **Not verified** because PostgreSQL could not start |

## Test coverage

The passing tests include agent approval denial, REVIEW/FAIL selection rejection, the ScamAdviser threshold, every forbidden historical category, incomplete/unverified evidence, maximum 20 candidates, cross-project rejection, confirmation and fixture acknowledgement, successful workflow transition and correlated approval audit, duplicate approval rejection, no purchase/payment endpoints, project-scoped agent permissions, CSRF/origin checks, logout, disabled fixtures, provider failure audit, rollback on audit failure, superseded approvals, and interrupted-run recovery.

The PostgreSQL suite is included and runnable with `docker compose --profile test run --build --rm integration-tests`. It additionally tests database-level audit immutability, finished-result/provenance immutability, the 21st candidate, and concurrent approval serialization. The same core API tests also run against PostgreSQL in that profile.

## Other observed failures and recovery

- npm's default cache path was not writable. Dependency installation succeeded using a workspace cache.
- The Next.js **development** server could not start its macOS FSEvent watcher in this sandbox. The **production build and standalone server** succeeded; the active preview uses that build.
- Direct headless Chrome startup from the shell failed in the sandbox. The successful browser walkthrough used the supported Codex in-app browser.
- The test dependency reports one Starlette deprecation warning about its current `httpx` test client. It did not fail the tests; dependencies are pinned in `requirements.lock`.

## Local preview

Open **http://localhost:3000**. `LOCAL-PREVIEW-ACCESS.txt` contains the temporary Owner login. The preview banner explicitly states that SQLite is being used and Docker/PostgreSQL are unverified. One synthetic demonstration project was created and approved during the browser walkthrough. This preview is not production infrastructure, and its health result must not be interpreted as PostgreSQL health.

For a clean Docker installation, use the README's setup commands. Docker starts with no Owner, no projects and no live providers; only the disabled Domain Research registry entry is seeded.

No purchases, payment operations, advertising, prohibited scraping, or next-stage agents were created or run.
