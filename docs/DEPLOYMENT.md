# Deployment and operation

## Supported topology

**For the requested Vercel frontend and Render backend, follow [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md).** The combined hosting option below remains available for local/container operation.

One FastAPI instance serves the built frontend and API behind an HTTPS reverse proxy. A PostgreSQL database can be managed externally; the application connects through a standard SQLAlchemy `postgresql+psycopg` URL. Private assets live on the instance's persistent disk, never in the public static directory. The local development alternative is SQLite on the same persistent volume. Multi-replica shared object storage and a distributed evaluation queue are not implemented.

Do not launch multiple SQLite workers. The process-wide transaction lock and PostgreSQL competition-row locks protect mutations, but polling, rate limiting, asset storage, and the background evaluation runner are designed for a single backend process. Benchmark the intended number of participants on the actual hosting environment before an event. Browser QA used two real teams, and the API suite tests concurrent requests; these are not a capacity benchmark.

## Environment

| Variable | Meaning |
| --- | --- |
| DATABASE_URL | `sqlite:///./data/promptpop.db` locally, or `postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE` for PostgreSQL |
| STORAGE_DIR | Private persistent asset directory, default `./data/assets` |
| APP_ORIGIN | Exact public origin including scheme; e.g. `https://event.example.org` |
| COOKIE_SECURE | Set `true` behind public HTTPS; sends Secure cookies and HSTS |
| SESSION_HOURS | Absolute session lifetime, default 12 |
| EVALUATOR_URL | Optional authorized HTTPS vision evaluator endpoint; empty disables it |
| EVALUATOR_SECRET | Optional server-only bearer secret for that evaluator |

URL-encode database credentials. Put real secrets in environment configuration, never in source control. For a proxy, forward Host and the public scheme; restrict trusted forwarded headers to the proxy's address. Keep all `/api` requests and the app on the same public origin. The server rejects foreign Origin and cross-site mutation requests. The `.env` file is ignored by Git.

## Container option

The supplied Dockerfile builds the Vite bundle and runs a non-root Python process. Example:

```sh
docker build -t promptpop .
docker run -d --name promptpop --env-file .env -p 127.0.0.1:8000:8000 -v promptpop-data:/app/data promptpop
docker exec -it promptpop python -m backend.cli organizer --generate
docker exec -it promptpop python -m backend.cli judge --role judge --generate
```

Terminate TLS through the hosting provider or reverse proxy. Set APP_ORIGIN to the public HTTPS domain and COOKIE_SECURE=true. Use an external PostgreSQL database for managed database operation, and mount persistent data for uploads. The Docker definition was source-reviewed; Docker was not available for a container build in this environment. Do not treat that as a tested public deployment.

The ORM creates the initial schema on first startup. There is no automatic schema-upgrade migration runner. For future schema changes, take backups and use a reviewed migration before upgrading an existing event. Do not point this version at an incompatible schema.

## Backups and recovery

Back up the database and the private asset directory together. Stop writes or use a consistent database snapshot; for SQLite use its backup API or stop the application rather than copying only the main file while WAL writes are active. For PostgreSQL use a managed snapshot or pg_dump. Asset identifiers in the database must match the private files in the snapshot.

Restarting the backend preserves rounds, deadlines, answers, drafts, submissions, approvals, sessions and audits. Clients restore official state by polling. A restart marks in-flight queued evaluations failed so judges can retry them. A browser refresh never resets the server timer. Accepted uploads survive browser refresh; unsubmitted file selections do not.

Expired sessions are rejected. Team access reset or disable revokes that team's sessions immediately. Bootstrap organizer and judge accounts from the trusted CLI. In an emergency, a second administrator account can be created locally; do not expose an unauthenticated password-reset route.

## Evaluator contract

`POST EVALUATOR_URL` receives a JSON object with submission_id, revision, round, prompt, rationale, brief, rubric, image_base64 and mime. An image-recreation task also supplies reference_base64. The configured bearer secret authenticates the request. The endpoint is administrator-controlled environment configuration, not a participant-supplied URL. Redirects are disabled and a 25-second timeout is applied.

Return:

```json
{"scores":[85,80,90,85],"explanations":["Composition reasoning","Lighting reasoning","Detail reasoning","Style reasoning"]}
```

Each score must be finite and in 0–100, in rubric order, with one bounded explanation per criterion. Invalid, failed and unavailable responses are recorded. No response changes official scores. Judges enter and approve their own final scores with a reason. Evaluation for an older revision is marked superseded. Do not send event assets to an evaluator until the organizer has authorized that service and its privacy/cost terms.

## Actual limitations

No verified ChatGPT capture extension, no ChatGPT conversation scraping, no verified generation-attempt telemetry, no external evaluator configured, no hosted identity provider, no multi-instance object-storage adapter, no public deployment or event-scale load test. These limits are visible in the product or documented here; manual event operation does not depend on them. The current client accepts still PNG/JPEG/WebP final images and evidence screenshots, with configurable task timing and server-enforced size/dimension limits. Other evidence export formats are not accepted.
