# Verification report

22–23 October 2026. Testing ran against the real built application on Windows with Python 3.12, Node.js 24, and headless Chromium. Automated browser fixtures use their own temporary server, database, accounts and test artwork. The live installation remains an unstarted event with no test teams or test reference assets.

## Results

| Gate | Result |
| --- | --- |
| TypeScript and Vite production build | Passed |
| Backend behavioral/security suite | 45 tests, including remote storage and health monitoring |
| PostgreSQL 17 backend suite in isolated GitHub CI | Passed with both default and private application schemas |
| Render Blueprint and Vercel config against official schemas | Passed |
| Vercel configuration rejection/routing tests | 2 passed |
| Separate HTTPS frontend proxy and API-only backend | Full competition journey passed; Secure cookies, private caching, API 404 and multipart upload above 4.5 MB verified locally |
| Supabase protocol tests | Private-bucket enforcement, persistence across clients, team isolation, ZIP export and rollback cleanup passed |
| Health monitor tests | Cold-start HTML retry and unsafe destination rejection passed |
| Chromium end-to-end competition journey | Passed |
| Browser runtime errors | None in the completed journey |
| axe accessibility checks | Zero reported violations in 20 captured desktop/mobile states |
| Mobile reflow | Checked at 390px and 320px; no page-level horizontal overflow |
| npm dependency audit | Zero reported vulnerabilities |

The backend test run emits one upstream Starlette TestClient deprecation warning concerning its current httpx compatibility path. It does not fail tests and does not affect the production HTTP server. This warning has not been hidden.

## Behavioral coverage

- Anonymous access is rejected. Participants cannot invoke organizer routes, edit scores, export private event data, fetch another team's uploads, or retrieve reference assets. Unreleased quiz content and case-study text remain unavailable to participants.
- Fifteen initial quiz questions load after release; answer keys never enter participant responses. Answer saves persist, stay isolated per team, and respect the official deadline. Pause/resume preserves remaining time; refresh retains the exact server deadline.
- The state machine rejects duplicate starts, skipped tasks, unsupported transitions, blank adjustment reasons, and content edits after release. Image-task count and rubrics are validated server-side.
- Manual uploads validate actual decoded image content, format, dimensions and size. Image and prompt are accepted without conversation evidence, with an explicit review flag and receipt. Drafts remain private. Concurrent team submissions persist correctly.
- Matching idempotency retries return the original receipt, including after the deadline. A changed payload with the same key is rejected. Revisions retain one scoring record. Grace-period acceptance is marked late; later work is rejected.
- Judges save review drafts, approve criterion scores, reject with a recorded reason, and reverse decisions with another audit entry. A stale revision is rejected. Rejected work retains its image and receives zero points.
- Missing/failed evaluations preserve submissions. A deliberately delayed evaluator in a protocol test does not block another team's state fetch or submission. This verifies isolation, not an actual external evaluator or model's quality.
- Approved-score weighting, missing-work zeroes, publication prerequisites, automatic unpublication after review changes, CSV formula neutralization, and private image/evidence ZIP export are tested.

## Browser journey

The browser registers a team through the actual form, signs in two teams, releases the quiz through a confirmation dialog, saves answers, refreshes, disconnects/reconnects a team, retries an unsaved answer, pauses and resumes the round, uploads creative work, restores its receipt, inspects side-by-side reference/submission images, saves/rejects/reverses a judge review, handles evaluator unavailability, releases a logo brief, submits the final logo, publishes results and downloads a CSV. The logo manual workflow is also exercised with browser local storage unavailable.

Focus containment is checked by tabbing around the native confirmation dialog. Authentication is completed using only the keyboard. Mobile navigation is exercised. Every capture runs axe WCAG A/AA rules and checks page-level overflow. Browser reports and screenshots are written to `test-results/combined/` and `test-results/split/`, with 20 captured states for each topology. The split run models the Vercel/Render request flow locally; cloud provider behavior still requires deployed verification.

## Design and usability refinement

| Finding | Correction |
| --- | --- |
| Initial supporting text was too faint and operational labels too small | Consolidated secondary text onto accessible ink and enlarged meaningful operational/reading text; verified contrast with the rendered audit |
| Empty-state action wrapped into its paragraph | Separate content block and centered action with deliberate spacing |
| Native dialog tab order could leave the document at its boundary | Explicit containment on Tab/Shift+Tab, with native Escape handling and focus restoration |
| Horizontally scrolling tables were not reachable by keyboard | Focusable named table regions with visible focus |
| Off-canvas navigation could stay keyboard reachable while closed | Hide it from the accessibility/focus tree until opened; focus the first item on open and support Escape |
| Controlled judge textarea label became unstable after saving | Explicit label/field association, with predictable editing after reload |
| Review reload could race the next edit | Await the saved review reload and disable fields during save |
| Browser storage could be unavailable | Local recovery cache is optional; server-backed drafts and manual submission remain usable |
| Evaluator network calls could delay competition transactions | Run external evaluation outside the live-state lock; store asynchronous, revision-aware results |
| A closed task could still display its future scheduled countdown | Closed tasks display zero and lead organizers to results after the final challenge |
| JPEG orientation metadata could be removed before applying its rotation | Normalize orientation before stripping metadata; verify the stored image dimensions |

## Deployed verification

On 23 October 2026, the free Render API and Vercel frontend were verified live. Both direct and proxied `/api/health` returned JSON 200. Anonymous `/api/me` and asset requests returned 401; unknown API routes returned 404. Organizer login through the Vercel origin succeeded with Secure, HttpOnly, SameSite=Strict cookies. Authenticated state, team and question endpoints returned 200 with no-store caching. A real browser reached the connected organizer control room. Organizer sessions and competition data survived a fresh backend redeployment. The event remained at round 0 with seven default tasks and no teams. Supabase startup checked the private bucket, and its security advisor reported no findings. The manually dispatched GitHub health workflow passed: [run 39892840175](https://github.com/akilomer06/prompt_pop/actions/runs/39892840175).

The deployed code passed [GitHub verification 39833091634](https://github.com/akilomer06/prompt_pop/actions/runs/39833091634), including PostgreSQL and both Chromium hosting topologies. Cloud screenshots are retained locally in `test-results/cloud/`.

## Practical limits

There is no claim of zero defects or a blanket accessibility certification. A manual screen-reader sweep, full 200% browser-zoom testing, Safari/Firefox/WebKit device coverage, event-scale load testing, the application Docker build and a full live-cloud competition/upload journey were not performed. Cloud checks preserved the empty official event. The backend suite passed on local SQLite and on an isolated PostgreSQL 17 service in GitHub's Linux CI. Both browser topologies were verified locally and on the Linux runner. The managed Render/Vercel deployment uses free plans, with persistent PostgreSQL and private uploads configured on Supabase Free. Free quotas and cold starts still apply.

ChatGPT authenticated session capture and generation-event tracking were not verified and are unavailable in the application. The primary adapter is deliberately not represented as working. No external vision evaluator is configured; manual judging is verified. These are the remaining integration boundaries described in RESEARCH.md and DEPLOYMENT.md.
