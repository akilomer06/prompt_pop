# Free hosting: Vercel + Render + Supabase

The frontend runs on Vercel, the FastAPI backend on Render Free, and PostgreSQL/private uploads on Supabase Free. Vercel proxies /api to Render, preserving host-only Secure cookies and team/role authorization. Supabase credentials stay on the backend; browsers never receive service keys or direct private storage URLs.

The root render.yaml now provisions **one free API service only**. It creates no paid disk or Render database. Supabase provides persistence independently of Render's temporary filesystem. Local SQLite and filesystem operation remain supported.

## Current setup

The free Supabase project is **Prompt Pop**, reference jdblbtjlpdfzwhybliab, in the user-selected **akilomer06's Org**, region Singapore. Its private bucket is promptpop-private. Application tables belong in the promptpop schema, outside the public Data API. A dedicated promptpop_app login has permission to create/use application objects in that schema. No credentials belong in this document.

## Deploy

1. Use Supabase's **session pooler** URL for IPv4 compatibility, with sslmode=require. Use the dedicated application login. The promptpop schema must exist and grant that login USAGE/CREATE. Keep it outside schemas exposed to the Data API.
2. Create the **private** promptpop-private Storage bucket. Add no anonymous read/upload policies. The backend needs a server-only secret/service-role key. Startup refuses a public bucket.
3. Apply the root render.yaml in the confirmed OmerAkil workspace. Verify the API plan is **Free**. Supply DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY and APP_ORIGIN privately. Keep workspace subscriptions and unrelated services unchanged.
4. Import akilomer06/prompt_pop into Vercel as **frontend only**: root frontend, Vite, Node 24, npm ci, npm run build, output dist. Set BACKEND_ORIGIN to the actual Render HTTPS origin without an /api suffix.
5. Set Render's APP_ORIGIN to the actual assigned Vercel production HTTPS origin, without a path/trailing slash. Complete this connection before sharing the app. Do not guess a domain or trust every *.vercel.app site.
6. Wait for healthy deployments. On Vercel, /api/health must return JSON, /api/me must return 401 before login, and unknown API paths must return 404. Sign in with the private organizer credentials. Restart Render and verify records, sessions and files survive.

## Health-check traffic

.github/workflows/health.yml requests backend readiness every ten minutes, offset from each hour's start. Set the repository Actions variable **RENDER_HEALTH_URL** to the actual https://your-service.onrender.com/api/health endpoint. Until configured, the workflow skips its job. A manual run is available. It requires JSON readiness, retries cold starts, sends no credentials and makes no event mutations.

This traffic can reduce idle cold starts. **It cannot guarantee an always-running free service.** GitHub may delay/drop jobs and disables public-repository schedules after 60 days without repository activity. Render can restart/suspend free services and enforces shared workspace quotas.

## Free limits

- Render Free sleeps after 15 idle minutes and may need about a minute to wake. Its 512 MB RAM and 750 instance hours/workspace/month are shared with other free services, including Talent Hunt. Keeping multiple services awake all month can exhaust that allowance.
- Free Render services cannot attach persistent disks. Render's free Postgres expires after 30 days; this configuration uses Supabase instead.
- Supabase Free currently includes 500 MB database storage, 1 GB file storage and 5 GB egress, with inactivity pausing and project limits. Revisions/evidence count toward file usage. Monitor capacity.
- The free API limits decoded images to 8 megapixels before loading them to fit memory; input files still have a 12 MB limit. PNG/JPEG/WebP normalization and metadata removal remain enforced.
- Optional external evaluators have separate costs and remain disabled unless authorized. Select free hosting plans only; do not enable paid upgrades, add-ons or automatic paid features.

## Backend settings

| Variable | Meaning |
| --- | --- |
| APP_ENV | production |
| SERVE_FRONTEND | false |
| COOKIE_SECURE | true |
| APP_ORIGIN | Exact Vercel production HTTPS origin |
| DATABASE_URL | Private SSL Supabase session-pooler URL |
| DATABASE_SCHEMA | promptpop |
| ASSET_STORAGE | supabase; development defaults to local |
| SUPABASE_URL | Exact project HTTPS origin |
| SUPABASE_SERVICE_ROLE_KEY | Server-only secret/service-role key, never VITE_ or publishable/anon |
| SUPABASE_BUCKET | promptpop-private |
| MAX_IMAGE_PIXELS | 8000000 on the free backend |
| BOOTSTRAP_ADMIN_PASSWORD | Private first-organizer secret; redeploys never reset existing admins |

Vercel needs only BACKEND_ORIGIN. GitHub's health workflow needs only RENDER_HEALTH_URL. Neither receives database/storage credentials. Private API responses use browser/CDN no-store policies. Upload failures roll back event changes and attempt to remove uncommitted objects.

Back up the database and bucket together. Provider outages and free quotas can interrupt timed events; test intended participant capacity. Protocol tests do not establish provider uptime guarantees.

References: [Render Free](https://render.com/docs/free), [Supabase pricing](https://supabase.com/pricing), [database connections](https://supabase.com/docs/guides/database/connecting-to-postgres), [private storage](https://supabase.com/docs/guides/storage/security/access-control), [GitHub schedules](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
