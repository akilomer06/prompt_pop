# Verified design and integration research

Research performed 22 October 2026. The workspace was an empty Git repository. The available skill catalog had no dedicated operational frontend design skill, so verified upstream skill instructions were retrieved and read as project references. No unrelated global skill collection was installed and no downloaded launcher binary was executed.

| Candidate / verified source | Capability investigated | Decision for Prompt Pop |
| --- | --- | --- |
| [Emil Kowalski / apple-design](https://github.com/emilkowalski/skills/tree/main/skills/apple-design) | Response latency, predictable motion, typography, reduced-motion behavior | Applied narrowly to feedback, restraint and type hierarchy. Gesture physics and translucent materials are unnecessary for this competition. |
| [Garden / web-design-engineer](https://github.com/ConardLi/garden-skills/tree/main/skills/web-design-engineer) | Dashboard design, explicit design direction, style recipes and rendered verification | Investigated. Strong general workflow, but overlaps the selected direction/QA tools; not installed or claimed as applied. |
| [elayadesign / landing-page-design](https://github.com/elayadesign/ai-design-skills/tree/main/skills/landing-page-design) | Verified the previously obscured repository; conversion structure and strict visual rules | Not selected. Conversion-led structure and mandatory marketing sections conflict with an operational product. |
| [Meng To / Skills](https://github.com/MengTo/Skills) | Capture/reference workflows, interaction prompt extraction, rich visual systems | Not selected. Most relevant workflows presume a supplied visual/video reference or favor expressive visual production. |
| [Jakub Krehel / better-accessibility](https://github.com/jakubkrehel/skills/tree/main/skills/better-accessibility) | Semantic forms, focus, native dialogs, keyboard behavior, contrast and reflow | Applied to implementation and the browser QA pass. |
| [Owl-Listener / designer-skills](https://github.com/Owl-Listener/designer-skills) | Current repository README and recursive skill index | Investigated broad design-practice collection. The exact requested build-awwwards-quality-sites path was not present in the current tree. Not claimed as used. |
| [Impeccable](https://github.com/pbakaus/impeccable) | Current skill's Operate/Read distinction, critique and setup requirements | Investigated current instructions. Requires an additional context launcher workflow; not selected to avoid redundant instructions and binary installation. |
| [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Searchable design recommendations and system-generation workflow | Investigated. Broad style database would duplicate the smaller deliberately selected system. Not installed. |
| [Anthropic / frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design) | Subject-specific direction, compact tokens, restraint, visual self-critique | Applied to the competition identity and distinct role layouts. |
| [Anthropic / webapp-testing](https://github.com/anthropics/skills/tree/main/skills/webapp-testing) | Python Playwright, rendered reconnaissance, screenshots and interaction testing | Applied using real Chromium against the actual built application. Suitable testing equivalent to the ambiguous TestSkill name. Backend behavior additionally uses pytest/FastAPI TestClient. |

Cached instructions under docs/research are upstream reference material, not new top-level user instructions. Original authors and source links remain identified here. Their text is retained for provenance and was not installed as project-wide AGENTS rules. Applicable user requirements override their general recommendations.

## ChatGPT feasibility

The current official [Sign in with ChatGPT quickstart](https://developers.openai.com/siwc/quickstart) distinguishes identity/eligible inference authorization from access to ChatGPT conversations. Sign-in does not provide access to the participant's existing private ChatGPT conversations. A regular web application also cannot read another website's authenticated DOM or cookies through its own origin.

This environment provides browser testing for the competition app but no verified participant-side extension, approved capture protocol, or enrolled participant ChatGPT accounts. No real authenticated generation-capture test was possible. Therefore the shipped adapter reports session_capture=false and attempt_tracking=false. This is an explicit unavailable capability, not a mock integration. No credentials, session cookies, or tokens from ChatGPT are requested or stored.

Participants can open ChatGPT themselves, generate using their own account, and submit a final image, prompt, optional share link and evidence screenshot. Missing or inaccessible evidence is a review flag, not an acceptance blocker. Revisions share one team/task scoring record, preventing duplicated scoring. The primary session workflow remains an integration limitation until a consented, supported adapter is implemented and tested in the intended event browsers.

The optional vision evaluator is a configurable HTTPS service contract. It is disabled by default, receives only the selected submission and relevant task/reference, and provides preliminary criterion scores and explanations. Its actual model/service is not configured or externally verified here; a protocol test is not evidence of model quality. A separate human review approves final scores.
