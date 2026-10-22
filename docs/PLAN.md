# Prompt Pop implementation plan

Build a local-first competition platform with a deployable React/Vite/TypeScript frontend and FastAPI/SQLAlchemy backend. PostgreSQL is supported through DATABASE_URL; SQLite provides a working development installation. Private assets stay outside the web root. A single application instance is the supported initial deployment, using polling for authoritative live state and cross-client recovery.

1. Inspect the empty repository, runtime, and verified design resources.
2. Establish broadcast-inspired navy/blue/white design tokens, distinct operational and focused layouts, semantic forms and keyboard interactions.
3. Implement durable server sessions, role checks, configurable teams, private assets, competition state machine, audit trail, authoritative timers and quiz autosave.
4. Build all seven tasks across three rounds, manual creative submissions, evidence, revision-safe receipts and draft recovery.
5. Implement review, configurable rubrics/round weights, score approval, result publication and CSV exports.
6. Keep session capture unavailable until proven; implement an isolated capability adapter and optional evaluator contract without pretending unavailable services work.
7. Verify security, state transitions, deadlines, idempotency, simultaneous teams, export, real rendered layouts, keyboard operation and responsive behavior.

Quality gates: production TypeScript build; backend behavioral/security suite; browser end-to-end journey; visual review at desktop and mobile; deployment documentation with explicit capability boundaries.
