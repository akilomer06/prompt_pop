# Prompt Pop 2K26 --- Product Requirements Document (PRD)

## 1. Objective

Act as a senior product architect, full-stack engineer, product
designer, UX researcher, security engineer, and QA lead. Build a
complete, production-quality web application for **Prompt Pop 2K26**, a
competitive AI prompting and creative design event.

Do not merely create a landing page, visual prototype, or dashboard
mockup. Build a working competition management platform with separate
admin and participant experiences, synchronized rounds, timed
challenges, submission handling, and automated judging wherever
feasible.

Before implementation, inspect the repository, environment, existing
dependencies, and available tools. Establish an implementation plan,
then execute it systematically.

## 2. Product vision

Prompt Pop is a multi-round competition where teams demonstrate AI
knowledge, prompt-writing ability, visual recreation skills, and
logo-design creativity.

The platform must support:

1.  **Round 1 --- AI Quiz:** 15 timed questions, automatic answer
    recording, server-controlled deadlines, and basic anti-cheating
    monitoring.
2.  **Round 2 --- AI Image Recreation:** Teams use their own ChatGPT
    sessions to recreate five reference images displayed by the admin.
    The primary workflow should use a technically feasible session-based
    integration; a manual submission workflow is mandatory as a
    fallback.
3.  **Round 3 --- AI Logo Design:** Teams receive a case study from the
    admin and create a logo using their own ChatGPT sessions. Use the
    same session-first workflow and manual fallback as Round 2.

The platform should reduce organizer workload while preserving fairness
and human oversight of final judging.

## 3. Users, roles, and access control

### Admin

The admin can:

-   Create and configure rounds.
-   Manage teams and participants.
-   Upload quiz questions, reference images, and case studies.
-   Configure timing, attempt limits, and scoring rubrics.
-   Start, pause, resume, and end rounds where permitted.
-   Reveal or advance tasks.
-   Monitor teams, timers, and submission status.
-   Review suspicious activity and integration failures.
-   Inspect submissions and conversation evidence.
-   Trigger or review automated evaluations.
-   Override scores with an audit trail.
-   Publish the final leaderboard.
-   Export submissions, scores, and results.

Protect admin routes and actions on the server. Hiding buttons in the
frontend is not sufficient authorization.

### Participant

Each team receives its own authenticated identity or access code.

Participants can:

-   View the current round and task.
-   See the official countdown.
-   Answer quiz questions.
-   Work through released creative tasks.
-   Use the supported ChatGPT session workflow.
-   Use the manual fallback if integration fails.
-   View their own prompts, attempts, and submission status.
-   Receive submission receipts and deadline notifications.

Participants must not access another team's private data, unreleased
questions, hidden reference assets, other teams' submissions, or admin
functions.

Support configurable team-based access rather than hard-coding a
specific team structure.

## 4. Round 1 --- AI Quiz

### Competition rules

-   Fifteen questions by default.
-   Admin-configurable question bank, answer options, timing, and
    marking.
-   Multiple-choice and other objectively gradable formats where
    supported.
-   The same approved quiz or equivalent randomized versions for all
    teams.
-   Optional randomization of question and answer-option order.
-   Correct answers remain hidden until authorized release.
-   Answers autosave to the server.
-   Answers saved before the deadline count; late answers follow the
    configured cutoff policy.
-   Unanswered questions receive no credit unless configured otherwise.

### Participant interface

Provide:

-   Current question number.
-   Question text or approved image.
-   Answer choices.
-   Question navigation where permitted.
-   Answered/unanswered indicators.
-   Countdown timer.
-   Autosave and connection status.
-   Clear deadline behavior.

### Anti-cheating measures

Use browser events where available:

-   `document.visibilitychange`
-   `window.blur`
-   `window.focus`
-   `fullscreenchange`

Record incident type, timestamp, and duration where available. Show
warnings according to configurable thresholds and provide an admin
incident log.

A normal website cannot completely lock the operating system or prevent
every form of application switching. Do not falsely claim otherwise.
Managed kiosk mode may be supported as a separately configured device
capability.

Do not automatically disqualify a team based solely on one fullscreen
exit or focus event. Let the admin review incidents according to the
published rules.

The server, not the participant's local clock, determines the official
deadline.

## 5. Round 2 --- AI Image Recreation

### Objective

Teams recreate five reference images shown on the admin-controlled
presentation screen. The participant site reveals the task number and
timer but must not expose private reference-image files through
participant APIs.

Suggested editable defaults:

-   Five images.
-   Ten minutes of creation per image.
-   Two-minute submission grace period, if needed.
-   Configurable attempt limit, such as three attempts per image.

Do not hard-code these settings.

### Primary workflow --- participants' own ChatGPT sessions

The preferred workflow uses participants' existing ChatGPT accounts and
subscriptions instead of paying for image generation through the
organizer's API account.

Investigate whether a legitimate, reliable session-based integration is
feasible for the actual target browser and ChatGPT interface.

A permissioned browser extension or another supported browser
integration may be considered if appropriate. Do not assume that a
normal webpage can read or control another website's authenticated
session.

Where technically and legitimately supported:

1.  Participants sign in to ChatGPT before the round.
2.  The platform connects to the participant's session with explicit
    consent.
3.  Prompts and generation events are associated with the correct team
    and task.
4.  Generated images and relevant attempt history are captured where
    supported.
5.  The final selected image and prompt evidence are submitted to the
    competition backend.
6.  Timestamps and integration status are recorded.
7.  Only relevant competition activity is collected.

Never collect passwords, authentication tokens, session cookies, or
unrelated private conversation history.

Be explicit about actual integration capabilities. Do not claim attempt
limits are enforced if generation events cannot be reliably observed.

### Mandatory fallback --- manual ChatGPT submission

If the integration fails, is unavailable, or cannot capture required
evidence, participants must still be able to submit through Prompt Pop.

Provide:

-   Automatically assigned team ID and task ID.
-   Final generated image upload.
-   Final prompt.
-   ChatGPT conversation link.
-   Optional conversation export or evidence screenshot.
-   Server-generated submission timestamp.
-   Submission confirmation.

Allow an image and prompt to be submitted even if the conversation link
is inaccessible. Flag missing evidence for review instead of blocking a
valid submission.

Prevent duplicate scoring when a team switches from the primary workflow
to the fallback. Preserve previously collected work.

### Automated image evaluation

Evaluate submitted images against the official reference using a
configurable rubric.

Suggested criteria:

-   Composition and layout: 30%.
-   Color and lighting: 20%.
-   Subject and detail accuracy: 25%.
-   Style and overall resemblance: 25%.

Use an authorized, verified vision-capable evaluator where available.
Store criterion-level scores, explanations, evaluation status, and
scoring method.

A computer-vision similarity measure may supplement rubric-based
evaluation. Neither similarity metrics nor model scores should be
treated as objective proof of creativity, originality, or cheating.

Allow judges to inspect borderline scores, flagged cases, and selected
ordinary submissions.

## 6. Round 3 --- AI Logo Design

### Objective

The admin reveals a business case study or brand brief. Teams create a
logo that meets the requirements, using their own ChatGPT sessions.

Use the same session-first workflow and manual fallback as Round 2.

### Admin setup

The admin can:

-   Write or upload the case study.
-   Define mandatory brand requirements.
-   Configure task duration.
-   Specify accepted image formats.
-   Configure the scoring rubric and criterion weights.
-   Preview the brief before releasing it.

### Primary ChatGPT session workflow

Where supported, collect relevant prompts, generated logo images, and
attempt history associated with the active task. Never collect unrelated
conversations or credentials.

### Manual fallback

Participants can submit:

-   Final logo image.
-   Final prompt.
-   ChatGPT conversation link.
-   Optional conversation export or evidence screenshot.
-   Optional short design rationale.

The fallback must work independently of the integration.

### Logo evaluation

Suggested default rubric:

-   Relevance to the case study: 30 points.
-   Originality and distinctiveness: 25 points.
-   Visual design and composition: 20 points.
-   Readability and scalability: 15 points.
-   Rationale and communication: 10 points.

AI produces preliminary scores and explanations. Judges make the final
decision and may override scores with an audit record.

Do not automatically label a logo as plagiarized merely because it
resembles a common design or another submission.

## 7. Shared live admin control room

Create the operational center of the competition.

Display:

-   Competition status.
-   Active round and task.
-   Official countdown.
-   Connected teams.
-   Submitted, pending, missing, late, and failed submissions.
-   Integration health and fallback usage.
-   Attempt counts where verifiable.
-   Recent integrity incidents.
-   Evaluation queue and exceptions.

Provide controls to configure, start, pause or resume where permitted,
reveal, advance, and end rounds; close submissions; trigger or retry
evaluations; review incidents; override scores; and publish results.

Use explicit confirmation for consequential actions.

Implement a server-side state machine to prevent invalid transitions,
duplicate starts, accidental task skipping, and unauthorized deadline
changes. Record administrative changes and permitted time adjustments in
an audit log.

Use WebSockets or another suitable real-time transport to synchronize
connected clients. On refresh or reconnection, restore the authoritative
state without resetting the timer.

## 8. Unified submissions and judging

Build a shared submission system for all rounds.

Store the appropriate combination of:

-   Team ID.
-   Round ID.
-   Task ID.
-   Prompt text.
-   Uploaded image or quiz answer.
-   Conversation link or evidence where relevant.
-   Submission timestamp.
-   Attempt number where applicable.
-   Evaluation status.
-   Criterion-level scores.
-   Judge notes and override history.

Support draft, submitted, late, rejected, awaiting evaluation,
evaluated, and manually reviewed states.

Use unique identifiers and database constraints to prevent duplicate
submissions from being scored twice.

### Judging dashboard

Provide:

-   Filters by round, task, team, status, and score.
-   Side-by-side reference/submission comparison for Round 2.
-   Logo gallery for Round 3.
-   Prompt and evidence inspection.
-   AI-generated criterion scores and explanations.
-   Judge score overrides and comments.
-   Manual review flags.
-   Final score approval and audit history.

Avoid requiring judges to open every conversation manually.

### Leaderboard

Aggregate approved scores across all rounds using configurable round
weights. Do not assume final weighting without making it configurable.

Provide a results preview, configurable tie-break rules, publication
controls, and CSV export containing team identity, round scores,
criterion-level results, and final ranking.

## 9. Technical architecture

Inspect the existing repository and reuse its working stack where
appropriate. If no suitable foundation exists, use this preferred
baseline.

### Frontend

-   React.
-   Vite.
-   TypeScript.
-   Tailwind CSS.
-   Accessible reusable components.
-   A consistent icon library.
-   WebSockets or equivalent real-time client support.

Separate public, admin, participant, and judging experiences. Organize
code by features and roles.

### Backend

-   Python.
-   FastAPI.
-   PostgreSQL through Supabase or an equivalent managed service.
-   Supabase Auth or another suitable authentication provider.
-   Private object storage for reference images and submissions.
-   WebSockets or equivalent real-time updates.
-   Modular evaluation services.

Suggested feature modules:

-   Authentication and team management.
-   Competition configuration.
-   Round and task management.
-   Quiz engine.
-   Timer and live-state manager.
-   Browser integrity logging.
-   ChatGPT session integration adapter.
-   Manual fallback submission service.
-   Private asset storage.
-   Image and logo evaluation.
-   Judge workspace.
-   Leaderboard and exports.
-   Audit and incident management.

Keep the ChatGPT integration isolated behind an adapter so the rest of
the platform remains functional when it fails.

### Database

Create appropriate relational tables or models for:

-   Users.
-   Teams and team memberships.
-   Competitions and rounds.
-   Tasks and task releases.
-   Quiz questions and answer options.
-   Team answers.
-   Integration sessions and health status.
-   Generation attempts.
-   Submissions and uploaded assets.
-   Evaluation runs and criterion-level scores.
-   Judge reviews.
-   Integrity incidents.
-   Audit events.

Use foreign keys, indexes, unique constraints, transactions, and
idempotent submission handling. Store large files in private object
storage rather than ordinary database rows.

### Security

-   Enforce server-side role-based access control.
-   Isolate team data through row-level security or equivalent controls.
-   Keep reference assets private until authorized release.
-   Validate uploads and reject unsupported or oversized files.
-   Keep secrets out of frontend code.
-   Use environment variables or a secret manager.
-   Validate every deadline and attempt on the server wherever
    verifiable.
-   Apply appropriate rate limits.
-   Use short-lived signed URLs where appropriate.
-   Never store ChatGPT credentials, session cookies, or authentication
    tokens.

Provide an `.env.example` with placeholder variable names only.

## 10. Cost and integration constraints

Do not make a paid image-generation API the default workflow. The
organizer wants participants to use their own ChatGPT accounts and
subscriptions to avoid paying for hundreds of image generations.

Verify session-integration feasibility in the actual target environment
before making dependent features rely on it.

Do not fake a ChatGPT integration or claim capabilities that have not
been tested.

Keep the manual fallback fully functional. Any optional paid evaluator
must be configurable, cost-aware, and unnecessary for basic event
operation.

## 11. Reliability and failure handling

Implement:

-   Automatic answer saving.
-   Explicit submission receipts.
-   Upload progress.
-   Retry handling for transient errors.
-   Duplicate-request protection.
-   Recovery after refresh or temporary disconnection.
-   Authoritative state restoration.
-   Integration health indicators.
-   Manual fallback submission.
-   Evaluation retries and manual scoring.
-   Clear error messages and deadline policies.

Never show a submission as successful before the server confirms
acceptance.

An integration or evaluation outage must not erase submissions or
prevent the competition from continuing.

## 12. Testing and quality assurance

Use appropriate testing skills and tools.

### Authentication and security tests

-   Admin routes reject unauthorized participants.
-   Teams cannot access other teams' private submissions.
-   Participants cannot retrieve unreleased reference assets.
-   Unauthorized score changes are rejected.

### Round 1 tests

-   Fifteen configured questions display correctly.
-   Answers persist.
-   Timers and deadlines remain synchronized.
-   Answers saved before the cutoff count.
-   Late answers follow the configured policy.
-   Integrity events are recorded.
-   Reconnection does not reset the timer.

### Round 2 and 3 tests

-   Correct tasks and briefs are released.
-   Deadlines are enforced.
-   Files and prompts are associated with the correct team and task.
-   Attempt limits are enforced only where verifiable.
-   Integration failures activate the manual fallback.
-   Duplicate submissions do not receive duplicate scores.
-   Failed evaluations can be retried.

### End-to-end tests

Simulate multiple teams participating simultaneously. Test timer
synchronization, task transitions, concurrent submissions, uploads near
deadlines, browser refresh, network disconnection, integration failure,
judge overrides, score calculations, and CSV exports.

Test the actual ChatGPT integration against the intended browser and
interface before claiming session capture or attempt counting works. A
mock response is not proof of a working integration.

## 13. Implementation plan

1.  Inspect the repository, environment, dependencies, and available
    tools.
2.  Produce a concise implementation plan and feature checklist.
3.  Establish the design system and key screen flows.
4.  Implement database models, authentication, team isolation,
    competition state, and timers.
5.  Build participant experiences for all three rounds.
6.  Build the admin control room and judging gallery.
7.  Implement the session-first integration and manual fallback.
8.  Implement evaluation, audit trails, leaderboard, and exports.
9.  Run automated and end-to-end tests.
10. Review the rendered application and refine usability and
    reliability.
11. Provide setup instructions, environment documentation, deployment
    guidance, test results, and a list of verified capabilities and
    remaining limitations.

## 14. Definition of done

The project is complete only when:

1.  Admin and participant roles have real server-side authorization.
2.  All three rounds are functional.
3.  Deadlines are enforced by the server.
4.  Answers and submissions persist correctly.
5.  The ChatGPT session integration has been tested and its capabilities
    documented honestly.
6.  Manual fallbacks work independently.
7.  Automated and AI-assisted evaluations can be reviewed and
    overridden.
8.  Judges can efficiently review submissions.
9.  Results and leaderboards can be exported.
10. The application passes relevant tests.
11. Setup and deployment instructions are complete.

**Final instruction:** Prioritize a reliable, polished competition
experience. Do not build a fake ChatGPT integration, do not use a paid
image-generation API as the default workflow, and do not sacrifice the
manual fallback. Make the session-based approach work where technically
supported, keep the rest of the platform independent of it, and ensure
organizers can run the event if the integration fails.
