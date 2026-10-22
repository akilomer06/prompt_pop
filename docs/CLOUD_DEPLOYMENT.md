# Vercel frontend + Render backend

The frontend is a Vite static build on Vercel. Vercel proxies `/api/:path*` directly to one Render FastAPI instance. Render PostgreSQL stores event state and a persistent disk stores private uploads. Browser URLs, downloads, cookies and uploads stay on the Vercel origin. No cross-origin browser authentication or CORS configuration is needed.

## Current deployment status

The configuration is prepared and locally verified. On 22 October 2026, activation stopped at Render's payment requirement at the owner's request. No Prompt Pop Render service, database or upload disk has been provisioned, and no Vercel production deployment has been created. The application is not publicly live. Resume the provider setup below only when paid hosting is authorized.

## Provider setup

1. Import `akilomer06/prompt_pop` into Vercel. Select **frontend as a standalone project**, root directory `frontend`, Vite, Node 24, `npm ci`, `npm run build`, output `dist`. Do not select the detected multi-service setup: the Python backend belongs on Render.
2. In the confirmed **OmerAkil** Render workspace, create a Blueprint from `main` and the root `render.yaml`. It defines `prompt-pop-api`, `prompt-pop-db`, and the API's 10 GB disk at `/var/data`, all in Singapore. Review the paid estimate before applying. The initial API plan is 1 CPU/2 GB RAM; PostgreSQL is 0.1 CPU/256 MB with 5 GB storage. Keep the existing workspace subscription unchanged. These are initial resource choices, not an event-capacity guarantee.
3. Supply **APP_ORIGIN** as the exact assigned Vercel production origin without a trailing slash or path. If the initial setup order requires assigning one provider's domain first, update the other provider's origin settings before testing or sharing the site. Do not enter an assumed domain.
4. Set **BACKEND_ORIGIN** in Vercel's Production environment to the actual Render HTTPS origin, without an `/api` suffix. `frontend/vercel.ts` fails configuration loading when this is absent or unsafe. This setting needs no `VITE_` prefix. Deploy after saving. Use a separate staging API/database for previews rather than granting every `*.vercel.app` site access to the live event.
5. Wait for Render readiness and Vercel deployment to succeed. On the Vercel domain, `/api/health` must return JSON, `/api/me` must return 401 before login, and unknown `/api/...` paths must return 404 instead of HTML. Confirm Render's APP_ORIGIN exactly matches the assigned production domain.
6. Render generates **BOOTSTRAP_ADMIN_PASSWORD** privately. Retrieve it from the API's environment settings and sign in as **organizer** on Vercel. First startup hashes it and creates the first administrator; redeploys never reset an existing administrator. After successful login, remove the bootstrap secret from Render and retain credentials in a password manager. A fresh empty database will need a new private bootstrap secret. Create additional judges in Render's trusted shell with `python -m backend.cli judge-name --role judge --generate`.
7. Verify private uploads/downloads and the largest allowed multipart upload through Vercel. Restart Render and confirm sessions, event records and uploaded images survive. Use an isolated staging event to test task releases, submissions, judging and publication; closing a task is final. Benchmark the intended participant count before event use.

## Settings

| Variable | Provider | Value or meaning |
| --- | --- | --- |
| APP_ENV | Render | `production` enables required hosting checks |
| SERVE_FRONTEND | Render | `false`; API only |
| APP_ORIGIN | Render | Exact assigned Vercel production HTTPS origin |
| APP_ORIGINS | Render | Optional extra exact HTTPS origins during a custom-domain transition; no wildcards |
| COOKIE_SECURE | Render | `true` |
| DATABASE_URL | Render | Blueprint private PostgreSQL connection string; standard Render URLs are normalized to the installed psycopg driver |
| PERSISTENT_DATA_DIR | Render | `/var/data`, attached persistent disk |
| STORAGE_DIR | Render | `/var/data/assets`, outside the static frontend |
| BOOTSTRAP_ADMIN_USERNAME | Render | `organizer` |
| BOOTSTRAP_ADMIN_PASSWORD | Render | Generated secret, used only when no administrator exists |
| BACKEND_ORIGIN | Vercel | Actual Render HTTPS origin, used by deployment routing configuration |

Never put passwords, database URLs or evaluator secrets in `VITE_` variables, browser code, source control or public logs. Optional evaluator configuration and backup procedures are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Operations

The backend runs one worker and one instance. Production startup requires PostgreSQL, Secure cookies, exact HTTPS origins and a private asset directory under the mounted persistent disk. The readiness endpoint checks a database connection and returns 503 without disclosing connection details when unavailable. Private API responses set browser and CDN `no-store` headers. Vercel independently applies CSP, HSTS and other security headers to static frontend responses.

Render's `autoDeployTrigger: checksPass` gates code deployments on GitHub CI. Vercel follows the connected production branch. Do not push a release during a timed round: Render persistent disks require stopping the previous instance, causing a short interruption. Initialization runs at application startup because disks are unavailable to build and pre-deploy commands. PostgreSQL schema creation is supported; future schema changes require reviewed migrations and backups.

The deployment uses paid Render compute, database and storage. Prices and included usage can change; review the provider's actual estimate. The selected compute currently costs $25/month for the API and $6/month for PostgreSQL, plus disk/database storage, bandwidth and any applicable taxes. No extra workspace subscription upgrade is required by this configuration.

## Verification boundary

Verification covers 35 backend tests on SQLite and PostgreSQL 17, provider schema validation, configuration routing/rejection tests and a full Chromium journey through a separate HTTPS frontend proxy to the API-only backend. The PostgreSQL suite runs against an isolated CI service; the test fixture rejects remote or live database URLs before dropping test tables. The split browser test checks Secure/HttpOnly/SameSite cookies and uploads above 4.5 MB. It models the topology; it does not emulate Vercel's infrastructure or prove a public deployment. Cloud URLs, the managed Render database connection and restart persistence must also be checked on the deployed resources. Event-scale load testing remains required.

Provider references: [Render Blueprint](https://render.com/docs/blueprint-spec), [persistent disks](https://render.com/docs/disks), [pricing](https://render.com/pricing), [Vercel TypeScript configuration](https://vercel.com/docs/project-configuration/vercel-ts), [external rewrites](https://vercel.com/docs/routing/rewrites).
