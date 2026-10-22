import { api, send } from "@/api";
import { Badge, Empty, Heading, ResourceError } from "@/components/ui";
import { dateTime, human } from "@/lib/helpers";
import { useResource } from "@/lib/useResource";
import type { Common, Submission, Task, Team } from "@/types";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  CheckCheck,
  ExternalLink,
  Image as ImageIcon,
  RefreshCw,
  Search,
} from "lucide-react";
import { useEffect, useState } from "react";
type EvalRun = {
  id: string;
  created: number;
  revision: number;
  status: string;
  method: string;
  result: { scores?: number[]; explanations?: string[]; message?: string };
};
type ReviewDetail = {
  submission: Submission;
  evaluations: EvalRun[];
  history: {
    action: string;
    timestamp: number;
    actor: string;
    details: Record<string, unknown>;
  }[];
};
export function Judging(props: Common & { refreshKey: number }) {
  const subs = useResource<Submission[]>("/submissions", [], props.refreshKey);
  const teams = useResource<Team[]>("/admin/teams", []);
  const [round, setRound] = useState("all");
  const [taskFilter, setTaskFilter] = useState("all");
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  const [minScore, setMinScore] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const filtered = subs.data.filter((s) => {
    const task = props.state.tasks.find((t) => t.id === s.task_id)!;
    const team = teams.data.find((t) => t.id === s.team_id);
    const score = s.scores ? scoreTotal(s.scores, task) : null;
    return (
      (round === "all" || task.round === Number(round)) &&
      (taskFilter === "all" || task.id === Number(taskFilter)) &&
      (status === "all" ||
        (status === "approved"
          ? s.approved
          : status === "flagged"
            ? s.evidence_flag || s.late
            : !s.approved)) &&
      (!minScore || (score !== null && score >= Number(minScore))) &&
      (team?.name || "").toLowerCase().includes(query.toLowerCase())
    );
  });
  return (
    <>
      <Heading
        title="Judging studio"
        description="Look closer. Score with purpose. Give every idea a fair review."
      >
        <a className="button secondary" href="/api/admin/export-assets">
          <ArrowDownToLine size={16} />
          Download images & evidence
        </a>
        <a
          className="button secondary"
          href="/api/admin/export?kind=submissions"
        >
          <ArrowDownToLine size={16} />
          Export submissions
        </a>
      </Heading>
      <ResourceError
        error={subs.error || teams.error}
        retry={() => {
          void subs.load();
          void teams.load();
        }}
      />
      {selected ? (
        <ReviewStudio
          key={selected}
          {...props}
          submissionId={selected}
          teams={teams.data}
          close={() => setSelected(null)}
          onSaved={() => {
            void subs.load();
            props.refresh();
          }}
        />
      ) : (
        <>
          <div className="filters">
            <label className="search-field">
              <Search size={17} />
              <input
                placeholder="Find a team"
                aria-label="Find submissions by team"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <label>
              <span className="sr-only">Round</span>
              <select
                value={round}
                onChange={(e) => {
                  setRound(e.target.value);
                  setTaskFilter("all");
                }}
              >
                <option value="all">All rounds</option>
                <option value="2">Image recreation</option>
                <option value="3">Logo design</option>
              </select>
            </label>
            <label>
              <span className="sr-only">Task</span>
              <select
                value={taskFilter}
                onChange={(e) => setTaskFilter(e.target.value)}
              >
                <option value="all">All tasks</option>
                {props.state.tasks
                  .filter(
                    (t) =>
                      t.round !== 1 &&
                      (round === "all" || t.round === Number(round)),
                  )
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.title}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              <span className="sr-only">Review status</span>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="all">Every status</option>
                <option value="pending">Awaiting approval</option>
                <option value="approved">Review complete</option>
                <option value="flagged">Flagged for review</option>
              </select>
            </label>
            <label className="min-score">
              <span className="sr-only">Minimum score</span>
              <input
                type="number"
                min={0}
                max={100}
                value={minScore}
                onChange={(e) => setMinScore(e.target.value)}
                placeholder="Min. score"
              />
            </label>
          </div>
          <div className="gallery-heading">
            <h2>
              Creative submissions <Badge>{filtered.length}</Badge>
            </h2>
            <span>Final decisions stay human.</span>
          </div>
          {filtered.length ? (
            <div className="judging-gallery">
              {filtered.map((s) => {
                const task = props.state.tasks.find((t) => t.id === s.task_id)!;
                return (
                  <button
                    className="judging-tile"
                    key={s.id}
                    onClick={() => setSelected(s.id)}
                  >
                    <div className="judging-image">
                      <img
                        src={"/api/assets/" + s.asset_id}
                        alt={`Creation by ${teams.data.find((t) => t.id === s.team_id)?.name || "team"}`}
                      />
                      <Badge tone={s.approved ? "success" : "light"}>
                        {s.status === "rejected"
                          ? "Rejected"
                          : s.approved
                            ? "Approved"
                            : "Review needed"}
                      </Badge>
                    </div>
                    <div className="judging-caption">
                      <div>
                        <h3>
                          {teams.data.find((t) => t.id === s.team_id)?.name ||
                            "Team"}
                        </h3>
                        <p>{task.title}</p>
                      </div>
                      <span className="gallery-score">
                        {s.scores ? scoreTotal(s.scores, task).toFixed(1) : "—"}
                        <small>/ 100</small>
                      </span>
                    </div>
                    <div className="judging-tile-footer">
                      <span>
                        {s.evidence_flag
                          ? "Evidence needs review"
                          : s.late
                            ? "Grace period submission"
                            : "Evidence provided"}
                      </span>
                      <ArrowRight size={16} />
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <Empty
              icon={ImageIcon}
              title={
                subs.data.length
                  ? "No submissions match these filters"
                  : "Every idea deserves a closer look"
              }
            >
              {subs.data.length
                ? "Change the round, team, status, or minimum score."
                : "Creative submissions will arrive here as teams complete their challenges. Review images side by side, inspect evidence, and score using the official rubric."}
            </Empty>
          )}
        </>
      )}
    </>
  );
}
const scoreTotal = (scores: number[], task: Task) =>
  scores.reduce((n, s, i) => n + (s * (task.rubric[i]?.weight || 0)) / 100, 0);
export function ReviewStudio(
  props: Common & {
    submissionId: string;
    teams: Team[];
    close: () => void;
    onSaved: () => void;
  },
) {
  const [detail, setDetail] = useState<ReviewDetail | null>(null);
  const [scores, setScores] = useState<number[]>([]);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const load = async () => {
    try {
      const d = await api<ReviewDetail>("/judging/" + props.submissionId);
      setErr("");
      setDetail(d);
      setScores(
        d.submission.scores ||
          props.state.tasks
            .find((t) => t.id === d.submission.task_id)!
            .rubric.map(() => 0),
      );
      setNotes(d.submission.notes);
    } catch (e) {
      setErr((e as Error).message);
    }
  };
  useEffect(() => {
    void load();
  }, [props.submissionId]);
  const evaluating = detail?.evaluations.some((run) => run.status === "queued");
  useEffect(() => {
    if (!evaluating) return;
    const interval = setInterval(() => {
      api<ReviewDetail>("/judging/" + props.submissionId)
        .then((next) => {
          setDetail(next);
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [evaluating, props.submissionId]);
  const s = detail?.submission;
  const task = props.state.tasks.find((t) => t.id === s?.task_id);
  return (
    <>
      <button className="text-button back-button" onClick={props.close}>
        <ArrowLeft size={16} />
        Back to gallery
      </button>
      <ResourceError error={err} retry={load} />
      {s && task && (
        <>
          <div className="review-heading">
            <div>
              <h2>
                {props.teams.find((t) => t.id === s.team_id)?.name || "Team"}
              </h2>
              <p>
                {task.title} · Revision {s.revision} · {dateTime(s.submitted)}
              </p>
            </div>
            <Badge tone={s.approved ? "success" : "blue"}>
              {s.status === "rejected"
                ? "Rejected"
                : s.approved
                  ? "Approved"
                  : "Awaiting approval"}
            </Badge>
          </div>
          <div className="review-layout">
            <div>
              <div
                className={
                  "comparison " + (task.round === 3 ? "logo-comparison" : "")
                }
              >
                {task.round === 2 && (
                  <figure>
                    <figcaption>Official reference</figcaption>
                    {task.reference_id ? (
                      <img
                        src={"/api/assets/" + task.reference_id}
                        alt="Official reference for comparison"
                      />
                    ) : (
                      <p>No reference asset available.</p>
                    )}
                  </figure>
                )}
                <figure>
                  <figcaption>Team creation</figcaption>
                  <img
                    src={"/api/assets/" + s.asset_id}
                    alt="Submitted creation under review"
                  />
                </figure>
              </div>
              <section className="evidence-panel">
                <h3>Prompt & evidence</h3>
                <p className="preserve">{s.prompt}</p>
                {s.rationale && (
                  <>
                    <h4>Design rationale</h4>
                    <p className="preserve">{s.rationale}</p>
                  </>
                )}
                {s.evidence_flag && (
                  <div className="banner warning">
                    Conversation evidence is missing. Review the image and
                    prompt on their merits; missing evidence is not proof of
                    misconduct.
                  </div>
                )}
                <div className="evidence-links">
                  {s.link && (
                    <a
                      className="button secondary"
                      href={s.link}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Conversation link
                      <ExternalLink size={15} />
                    </a>
                  )}
                  {s.evidence_id && (
                    <a
                      className="button secondary"
                      href={"/api/assets/" + s.evidence_id}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Evidence screenshot
                      <ExternalLink size={15} />
                    </a>
                  )}
                </div>
                <small>Receipt {s.receipt}</small>
              </section>
              <details className="history-panel">
                <summary>
                  Review & revision history ({detail!.history.length})
                </summary>
                {detail!.history.map((h, i) => (
                  <div key={i}>
                    <strong>{human(h.action)}</strong>
                    <small>{dateTime(h.timestamp)}</small>
                    <pre>{JSON.stringify(h.details, null, 2)}</pre>
                  </div>
                ))}
              </details>
            </div>
            <aside className="scoring-panel">
              <div className="section-title">
                <h3>Rubric scoring</h3>
                <Badge>Human review</Badge>
              </div>
              <p>
                Score each criterion from 0 to 100. Weights are applied
                automatically.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  props.confirm({
                    title: "Approve these scores?",
                    description:
                      "These criterion scores will count toward the results. Your decision and notes will be recorded. Later changes unpublish the results for review.",
                    label: "Approve scores",
                    action: async () => {
                      await api(
                        "/judging/" + s.id,
                        send("PUT", {
                          scores,
                          notes,
                          approved: true,
                          revision: s.revision,
                        }),
                      );
                      props.notify("Scores approved and recorded.");
                      props.onSaved();
                      await load();
                    },
                  });
                }}
              >
                {task.rubric.map((r, i) => (
                  <label className="score-input" key={r.name}>
                    <span>
                      {r.name}
                      <small>{r.weight}% of task score</small>
                    </span>
                    <input
                      aria-label={r.name + " score"}
                      disabled={busy}
                      type="number"
                      min={0}
                      max={100}
                      step={0.1}
                      required
                      value={scores[i] ?? 0}
                      onChange={(e) =>
                        setScores((v) =>
                          v.map((n, j) =>
                            j === i ? Number(e.target.value) : n,
                          ),
                        )
                      }
                    />
                  </label>
                ))}
                <div className="weighted-score">
                  <span>Weighted task score</span>
                  <strong>
                    {scoreTotal(scores, task).toFixed(1)}
                    <small>/100</small>
                  </strong>
                </div>
                <div className="review-notes">
                  <label htmlFor="judge-notes">
                    Judge notes / override reason
                  </label>
                  <textarea
                    id="judge-notes"
                    disabled={busy}
                    required
                    minLength={3}
                    maxLength={10000}
                    rows={4}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Explain the decision against the rubric."
                  />
                </div>
                {task.status !== "ended" && (
                  <div className="banner warning">
                    Scores can be approved once the organizer closes this task.
                  </div>
                )}
                <button
                  className="button primary wide"
                  disabled={busy || task.status !== "ended"}
                >
                  <CheckCheck size={17} />
                  Approve scores
                </button>
                <div className="review-secondary-actions">
                  <button
                    type="button"
                    className="button secondary"
                    disabled={busy || task.status !== "ended"}
                    onClick={async () => {
                      if (notes.trim().length < 3) {
                        setErr("Add review notes before saving a draft.");
                        return;
                      }
                      setBusy(true);
                      try {
                        await api(
                          "/judging/" + s.id,
                          send("PUT", {
                            scores,
                            notes,
                            approved: false,
                            revision: s.revision,
                          }),
                        );
                        props.notify(
                          "Review saved as a draft. It does not count until approved.",
                        );
                        props.onSaved();
                        await load();
                      } catch (e) {
                        setErr((e as Error).message);
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Save review draft
                  </button>
                  <button
                    type="button"
                    className="button danger-quiet"
                    disabled={busy || task.status !== "ended"}
                    onClick={() => {
                      if (notes.trim().length < 3) {
                        setErr(
                          "Explain the reason for rejection in the judge notes.",
                        );
                        return;
                      }
                      props.confirm({
                        title: "Reject this submission?",
                        description:
                          "This finalizes the review with zero points. The uploaded work is preserved, and your reason is recorded. A later reversal requires another recorded review.",
                        label: "Reject submission",
                        danger: true,
                        action: async () => {
                          await api(
                            "/judging/" + s.id,
                            send("PUT", {
                              scores: scores.map(() => 0),
                              notes,
                              approved: true,
                              reject: true,
                              revision: s.revision,
                            }),
                          );
                          props.notify(
                            "Submission rejected with a recorded reason.",
                          );
                          props.onSaved();
                          await load();
                        },
                      });
                    }}
                  >
                    Reject submission
                  </button>
                </div>
              </form>
              <div className="ai-review">
                <h4>Preliminary vision evaluation</h4>
                <p>
                  {props.state.integration.evaluator_configured
                    ? "Request a preliminary rubric assessment. It will never automatically approve a score."
                    : "No authorized evaluator is configured. Manual judging remains fully available."}
                </p>
                <button
                  className="button secondary wide"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      const r = await api<{
                        status: string;
                        result: { message?: string };
                      }>("/judging/" + s.id + "/evaluate", { method: "POST" });
                      props.notify(
                        r.result.message ||
                          "Preliminary evaluation complete. Review the explanation below.",
                      );
                      void load();
                    } catch (e) {
                      setErr((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <RefreshCw size={15} />
                  {busy
                    ? "Evaluating…"
                    : detail!.evaluations.length
                      ? "Retry evaluation"
                      : "Check evaluator"}
                </button>
                {detail!.evaluations.map((e) => (
                  <div className="evaluation-run" key={e.id}>
                    <Badge
                      tone={e.status === "evaluated" ? "success" : "amber"}
                    >
                      {e.status}
                    </Badge>
                    <small>
                      Revision {e.revision} · {dateTime(e.created)}
                    </small>
                    {e.result.message && <p>{e.result.message}</p>}
                    {e.result.scores?.map((v, i) => (
                      <p key={i}>
                        <strong>
                          {task.rubric[i]?.name}: {v}/100
                        </strong>
                        <br />
                        {e.result.explanations?.[i]}
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            </aside>
          </div>
        </>
      )}
    </>
  );
}
