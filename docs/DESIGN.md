# Prompt Pop design system

This is a live creative competition. Operational clarity and confidence come first. The memorable brand gesture is a pair of interlocking prompt-pop letterforms on the entrance poster; inside the application, the official clock and actual creative work carry the emphasis.

## Direction and critique

The starting direction was a competition broadcast desk: navy stage, blue action, warm white work surfaces, orderly run of show. A review against the brief removed decorative charts, ornamental motion, sample teams, pretend generation counts, and repeated metric tiles. The control room uses one stage, a chronological run of show, a single statistics strip, and a team table. Participants receive a narrow task navigator and answer sheet; creative tasks use brief/workspace columns; judging uses image comparisons with a rubric inspector.

Selected skills are recorded in RESEARCH.md. Their instructions were read before application. Frontend-design informed the poster, restrained interior, distinct workflow compositions and real empty states. Apple-design informed immediate press feedback, stable component behavior and reduced-motion handling. Better-accessibility informed native controls, semantic fields, focus trapping, keyboard scrolling, explicit status labels, and the contrast remediation. Webapp-testing informed rendered discovery, screenshots, real Chromium interactions, and a separate test database.

## Tokens

| Role | Value | Purpose |
| --- | --- | --- |
| Stage navy | #162947 | Event identity and presentation screen |
| Action blue | #2458DD | Primary actions, active task and selection |
| Paper | #FFFFFF | Editable work and review surfaces |
| Canvas | #F5F7FA | Separation of operational regions |
| Secondary ink | #52637D | Accessible supporting text |
| Warm accent | #EFB77A | Entrance identity only |

Manrope is bundled locally; no external font request is required. Headings tighten tracking; body copy keeps natural spacing. Timers use tabular numerals. The local CSS owns semantic colors, spacing, sizing and component states; Tailwind supplies the foundation without dictating page composition.

Spacing uses a 4px rhythm with 20–36px work-region padding. Controls use a 7px radius, structural regions 9–10px, the brand symbol 11px, and avatars use circles. These geometries convey different roles. Motion is limited to short action feedback, enabled only when reduced motion is not requested. There are no ambient animations.

## Workflow structure

```
Organizer: navigation | heading + controls
                      | official stage + run of show
                      | single event statistics strip
                      | team monitor + readiness

Quiz:     round progress
          task + official clock
          question index | question + answers

Creative: task + official clock
          brief / rules  | upload + prompt + evidence + receipt

Judging:  filters / gallery
          reference + creation | criterion scores + decision
          evidence / history  | preliminary evaluation
```

At mobile widths, operational regions stack; the navigation opens from its explicit menu control; tables scroll inside keyboard-focusable regions. Creative briefs precede upload controls. A 320px viewport is part of the browser verification.

## Interaction contract

- The server confirms answer saves and accepted submissions. Local unsaved answers are visually distinguished and can be retried.
- Official deadlines are epoch timestamps. Refresh never recreates them. The UI estimates server offset using request midpoint timing and resynchronizes every 2.5 seconds.
- Consequential controls open a native dialog, contain keyboard focus, support Escape, and wait for an acknowledged server mutation.
- Focus loss is a review signal; it never causes automatic disqualification.
- Rubric scoring never silently adopts an AI recommendation. A judge supplies criterion scores and a reason.
- ChatGPT capabilities are visible and honest: manual workflow active, capture unverified, attempts not independently counted.

Rendered visual and accessibility findings and their fixes are recorded in QA.md. Automated checks supplement visual review; they do not certify accessibility for every assistive technology.
