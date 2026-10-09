# Verification — 9 October 2026

The local Docker Compose deployment uses PostgreSQL and serves the frontend at **http://localhost:3001**. PostgreSQL, backend, and frontend were healthy after deploying the project rename/delete update. The one-shot migration service exited successfully; the database is at revision `0003_project_management`.

The PostgreSQL integration suite passed **45 tests**, including the existing domain authorization and evaluation rules, database integrity and concurrent approval tests, plus Owner-only project rename and delete tests. New tests cover blank names, exact deletion confirmation, audit retention, pending approval closure, agent credential revocation, interrupted research, and deletion of a previously approved project. The frontend TypeScript check and production build passed. `git diff --check` passed.

The pre-existing live project remained in `BRAND_PENDING` after deployment. No live project was renamed or deleted during verification. A PostgreSQL backup was saved outside the repository before migration.

The test runner emitted two non-failing warnings: a Starlette test-client deprecation and inability to write pytest's optional cache as the non-root container user. Neither affected test results.

The earlier SQLite preview and Docker startup limitations from 8 October no longer describe the current deployment. Domain research results remain synthetic fixtures unless an authorized provider is configured.
