import { Badge, Empty, Heading, ResourceError, Timer } from "@/components/ui";
import { roundIcons, roundNames } from "@/lib/helpers";
import { useResource } from "@/lib/useResource";
import type { Common, Submission, Team } from "@/types";
import {
  ArrowRight,
  Check,
  CheckCheck,
  ClipboardList,
  Image as ImageIcon,
  Monitor,
  Plus,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from "lucide-react";
export function ControlRoom(props: Common & { go: (s: string) => void }) {
  const { state, go } = props;
  const teams = useResource<Team[]>("/admin/teams", []);
  const subs = useResource<Submission[]>("/submissions", []);
  const task =
    state.tasks.find((t) => t.id === state.current) || state.tasks[0];
  const next = state.tasks.find((t) => t.id === state.current + 1);
  const active = task.status === "running" || task.status === "paused";
  const shown = active ? task : next || task;
  const currentSubs = subs.data.filter((s) => s.task_id === task.id);
  return (
    <>
      <Heading
        title="Control room"
        description="The whole competition. One clear view."
      >
        <button className="button secondary" onClick={() => go("present")}>
          <Monitor size={17} />
          Presentation screen
        </button>
        <button className="button primary" onClick={() => go("rounds")}>
          <SlidersHorizontal size={17} />
          Manage rounds
        </button>
      </Heading>
      <ResourceError
        error={teams.error || subs.error}
        retry={() => {
          void teams.load();
          void subs.load();
        }}
      />
      <div className="control-top">
        <section className="live-stage">
          <div className="stage-top">
            <Badge tone={active ? "live" : "light"}>
              <span className="status-dot" />
              {task.status === "running"
                ? "On the clock"
                : task.status === "paused"
                  ? "Competition paused"
                  : next
                    ? "Ready to begin"
                    : "Competition complete"}
            </Badge>
            <span className="stage-event">Event control / 2026</span>
          </div>
          <div className="stage-body">
            <div>
              <div className="round-kicker">
                Round {shown.round} of 3 <span>/</span>{" "}
                {roundNames[shown.round - 1]}
              </div>
              <h2>{shown.title}</h2>
              <p>
                {active
                  ? "Every team shares this official deadline."
                  : next
                    ? "Set the stage. Your next challenge is ready for review."
                    : "All challenges are closed. Review scores and publish the results."}
              </p>
            </div>
            <Timer task={shown} state={state} large />
          </div>
          <div className="stage-bottom">
            <span>
              <ShieldCheck size={16} />
              Authoritative server clock
            </span>
            <button
              className="stage-link"
              onClick={() => go(!active && !next ? "leaderboard" : "rounds")}
            >
              {active
                ? "Open round controls"
                : next
                  ? "Review & release"
                  : "Review results"}
              <ArrowRight size={17} />
            </button>
          </div>
        </section>
        <section className="run-of-show">
          <div className="section-title">
            <h2>Run of show</h2>
            <span>3 rounds</span>
          </div>
          {roundNames.map((name, i) => {
            const list = state.tasks.filter((t) => t.round === i + 1);
            const done = list.every((t) => t.status === "ended");
            const live = list.some((t) =>
              ["running", "paused"].includes(t.status),
            );
            const I = roundIcons[i];
            return (
              <button
                className={"round-line " + (live ? "current" : "")}
                key={name}
                onClick={() => go("rounds")}
              >
                <span className="round-number">
                  {done ? <Check size={17} /> : String(i + 1).padStart(2, "0")}
                </span>
                <span>
                  <strong>{name}</strong>
                  <small>
                    {i === 0
                      ? `${state.quiz_question_count} questions`
                      : i === 1
                        ? `${list.length} creative challenges`
                        : "1 brand brief"}
                  </small>
                </span>
                <Badge tone={done ? "success" : live ? "blue" : "neutral"}>
                  {done ? "Closed" : live ? "Active" : "Upcoming"}
                </Badge>
              </button>
            );
          })}
        </section>
      </div>
      <div className="stats-strip">
        <Stat
          icon={Users}
          label="Teams registered"
          value={teams.data.length}
          caption={`${teams.data.filter((t) => t.online).length} online now`}
        />
        <Stat
          icon={CheckCheck}
          label={
            task.round === 1 ? "Quiz answers saved" : "Current submissions"
          }
          value={
            task.round === 1
              ? teams.data.reduce((s, t) => s + t.answers, 0)
              : currentSubs.length
          }
          caption={
            task.round === 1
              ? "Persisted on the server"
              : `${Math.max(0, teams.data.length - currentSubs.length)} ${teams.data.length - currentSubs.length === 1 ? "team" : "teams"} ${task.status === "ended" ? "did not submit" : "yet to submit"}`
          }
        />
        <Stat
          icon={ImageIcon}
          label="Awaiting review"
          value={subs.data.filter((s) => !s.approved).length}
          caption={`${subs.data.filter((s) => s.approved).length} decisions finalized`}
        />
        <Stat
          icon={ShieldCheck}
          label="Integrity events"
          value={teams.data.reduce((s, t) => s + t.incidents, 0)}
          caption="Human review required"
        />
      </div>
      <div className="control-bottom">
        <section className="panel team-monitor">
          <div className="panel-header">
            <div>
              <h2>Team monitor</h2>
              <p>Participation across the competition.</p>
            </div>
            <button className="text-button" onClick={() => go("teams")}>
              Manage teams
              <ArrowRight size={15} />
            </button>
          </div>
          {teams.data.length ? (
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Competition data table"
            >
              <table>
                <thead>
                  <tr>
                    <th>Team</th>
                    <th>Connection</th>
                    <th>Quiz</th>
                    <th>Creative work</th>
                    <th>Integrity</th>
                  </tr>
                </thead>
                <tbody>
                  {teams.data.slice(0, 8).map((t, i) => (
                    <tr key={t.id}>
                      <td>
                        <span className="team-name">
                          <span className={"team-avatar color-" + (i % 4)}>
                            {t.name.slice(0, 2).toUpperCase()}
                          </span>
                          <strong>{t.name}</strong>
                        </span>
                      </td>
                      <td>
                        <Badge tone={t.online ? "success" : "neutral"}>
                          {t.online ? "Online" : "Offline"}
                        </Badge>
                      </td>
                      <td>{t.answers} saved</td>
                      <td>{t.submissions} received</td>
                      <td>
                        {t.incidents ? (
                          <Badge tone="amber">{t.incidents} events</Badge>
                        ) : (
                          <span className="muted">No events</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty icon={Users} title="Your teams take the stage here">
              Register the first team to issue a private access code and start
              tracking participation.
              <button className="button secondary" onClick={() => go("teams")}>
                <Plus size={16} />
                Register a team
              </button>
            </Empty>
          )}
        </section>
        <aside className="ops-notes">
          <div className="section-title">
            <h2>Event readiness</h2>
            <ShieldCheck size={18} />
          </div>
          <div className="readiness-item">
            <span className="check-circle">
              <Check size={13} />
            </span>
            <div>
              <strong>Manual submission is ready</strong>
              <p>Image, prompt, evidence, and a server-confirmed receipt.</p>
            </div>
          </div>
          <div className="readiness-item">
            <span className="info-circle">
              <Monitor size={14} />
            </span>
            <div>
              <strong>ChatGPT capture unavailable</strong>
              <p>
                Teams use their own sessions. Attempts are not independently
                verified.
              </p>
            </div>
          </div>
          <div className="readiness-item">
            <span className="info-circle">
              <ClipboardList size={14} />
            </span>
            <div>
              <strong>
                {state.integration.evaluator_configured
                  ? "Vision evaluator configured"
                  : "Judges stay in control"}
              </strong>
              <p>
                {state.integration.evaluator_configured
                  ? "Preliminary evaluations require final human approval."
                  : "Manual rubric scoring is available. No paid evaluator is required."}
              </p>
            </div>
          </div>
          <button className="text-button" onClick={() => go("settings")}>
            Review event settings
            <ArrowRight size={15} />
          </button>
        </aside>
      </div>
    </>
  );
}
export function Stat({
  icon: I,
  label,
  value,
  caption,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  caption: string;
}) {
  return (
    <div className="stat">
      <div className="stat-label">
        {label}
        <I size={18} />
      </div>
      <strong>{value.toString().padStart(2, "0")}</strong>
      <small>{caption}</small>
    </div>
  );
}
