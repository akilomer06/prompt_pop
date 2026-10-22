# Prompt Pop 2K26

A working competition platform with organizer, participant and judge workspaces. React + TypeScript + Vite/Tailwind frontend; FastAPI + SQLAlchemy backend; PostgreSQL support and a zero-service SQLite local setup. Assets are privately stored outside the frontend web root.

## Open the existing local installation

The application is available at **http://127.0.0.1:8000** when the local server is running. Organizer credentials were generated into the ignored `local-access.txt` file. There is no built-in or shared default password. Use `scripts/start.ps1` to start the built application and `scripts/stop.ps1` to stop the server managed by that script.

```powershell
.\scripts\start.ps1
```

## Fresh setup

Requires Python 3.12+ and Node.js 22.12+ (this implementation was tested with Python 3.12 and Node 24). From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m backend.cli organizer --generate
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

On macOS/Linux replace `.venv\Scripts\python.exe` with `.venv/bin/python` and `npm.cmd` with `npm`. Create a separate judge with `python -m backend.cli judge-name --role judge --generate`. Save generated passwords privately; they are printed only once. Organizer accounts are created through the local CLI, never through a public registration endpoint.

For development, run the backend on port 8000 and `npm --prefix frontend run dev` in a second terminal. Vite serves http://localhost:5173 and proxies `/api` to FastAPI. The local combined build can be served from FastAPI. Cloud hosting uses **Vercel for the frontend, Render Free for the backend and Supabase Free for persistent database/private images**, with `/api` proxied through Vercel. See the [cloud deployment guide](docs/CLOUD_DEPLOYMENT.md), including the ten-minute readiness monitor and free-tier limits.

Copy `.env.example` to `.env` if configuration is needed, and pass `--env-file .env` to uvicorn. The helper start script does this automatically if `.env` exists. Environment variables are read on backend startup. No secrets enter the frontend bundle.

## Run an event

1. Sign in as the organizer. Configure round weights, tie-break policy, and the image challenge count in Event settings **before** uploading references or starting the event.
2. Register teams. Copy each team's generated account/code privately. Members are configurable; there is no fixed team size. Access reset revokes existing sessions.
3. Review the editable 15-question starting bank, timing, image-task rubrics and private references. Write the logo case study and preview it. Reference images must be provided by the organizer; none are fabricated in the live event.
4. Open Presentation screen on the shared display. Release tasks in sequence from Rounds & content. Start, pause, resume, close and time-extension actions are validated and audited on the server. Closing a task is final.
5. Teams answer the quiz and create images/logos in their own ChatGPT sessions. They upload the selected result and final prompt. Share links and screenshots are optional; missing evidence is flagged for review. Accepted entries receive a durable server receipt.
6. Close creative tasks before approving scores in Judging studio. Inspect comparisons, prompts, evidence and prior reviews; score each criterion from 0–100 and explain the decision. AI recommendations are preliminary and never approve themselves.
7. Review standings, approve all received submissions, close all tasks, then publish results. Missing work receives zero. Export results/criteria to CSV, submission metadata to CSV, or images/evidence plus manifest to ZIP.

## Fairness and persistence

The server owns deadlines, cutoff policy, pause state, and task releases. Clients resynchronize every 2.5 seconds using the authoritative state and a request-midpoint clock offset. Refresh does not restart a timer. Quiz answers are saved per question; rejected/offline saves are clearly marked and retained locally for an explicit retry before cutoff. Only acknowledged answers count.

Creative grace periods accept entries marked late until the configured grace deadline. No new entry is accepted after that cutoff or after manual closure. A retry using the same request key returns the original accepted receipt even if the deadline has since passed. A different payload with that key is rejected. A unique team/task record prevents revisions from scoring twice. Revision history and earlier asset identifiers are preserved in the audit log.

Prompt/link/rationale drafts persist on the server and locally per team/task. Unsaved selected files must be reselected after a refresh; accepted uploaded files persist. Do not clear browser storage during a timed task with unsaved answers. Only data specific to the signed-in team is returned to participants.

## Verified capability boundary

All three competition rounds, manual creative workflows, role protection, deadlines, judging, approved-score rankings, publication and exports operate locally. **ChatGPT session capture and independently verified generation-attempt counting are unavailable.** No real authenticated capture integration was validated. No ChatGPT passwords, cookies or tokens are collected. See [research and feasibility](docs/RESEARCH.md).

The optional authorized HTTPS vision evaluator is disabled unless configured. Its queue runs outside the competition transaction so an evaluator outage cannot hold up team submissions. Failed/interrupted evaluations can be retried; human scoring works independently. No external model/service has been commissioned or verified. The interface labels these limitations explicitly.

This repository supplies deployment configuration; it has not been deployed to a public hosting account or load-tested at event scale. The supported initial topology is one backend instance with persistent private storage. See [deployment](docs/DEPLOYMENT.md) before hosting a live event.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe tests/e2e_browser.py
node --test tests/vercel-config.test.mjs
.\.venv\Scripts\python.exe scripts/validate-hosting.py
$env:E2E_SPLIT_HOSTING='1'
.\.venv\Scripts\python.exe tests/e2e_browser.py
```

Browser tests create an isolated temporary database/server on port 8011 and do not populate the live event. They exercise real Chromium with two teams, offline retry, timers, uploads, receipt recovery, comparison judging, result publication, CSV download, native dialogs, mobile reflow and axe accessibility scans. Screenshots and a JSON report appear under ignored `test-results/`. The report captures actual test data, not fabricated live statistics. Test fixtures are not an official event reference set.

See [QA results](docs/QA.md), [design system](docs/DESIGN.md), [implementation plan](docs/PLAN.md), and [skill research](docs/RESEARCH.md).

## Source layout

- `frontend/src/features`: organizer, participant, judging, authentication and results experiences.
- `frontend/src/components`: shared semantic controls, dialogs, timer and recovery boundary.
- `backend/models.py`: relational persistence, uniqueness constraints and foreign keys.
- `backend/app.py`: authorized API, state transitions, private uploads and exports.
- `backend/security.py`: password hashing, opaque hashed sessions and role checks.
- `backend/integrations.py`: explicit capability boundary and optional evaluator contract.
- `tests`: backend security/behavior tests and the isolated browser journey.

Upstream skill reference attribution is documented in `docs/RESEARCH.md`. Application code is separate from those reference instructions.
