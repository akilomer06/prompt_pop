import { api, send, upload } from "@/api";
import { Badge, Empty, Heading, ResourceError, Timer } from "@/components/ui";
import { dateTime, roundNames, shortTime } from "@/lib/helpers";
import { useResource } from "@/lib/useResource";
import { readLocal, writeLocal } from "@/lib/storage";
import type { Common, Submission, Task, User } from "@/types";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCheck,
  Clock3,
  ExternalLink,
  Flag,
  Image as ImageIcon,
  Maximize2,
  Monitor,
  Radio,
  RefreshCw,
  ShieldCheck,
  Upload,
  WandSparkles,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
export function Workspace(props: Common & { user: User; connected: boolean }) {
  const task = props.state.tasks.find((t) => t.id === props.state.current);
  return (
    <>
      <Heading
        title={props.user.team_name || "Your workspace"}
        description="Stay curious. Stay focused. Make your next prompt count."
      >
        <Badge tone="blue">Participant workspace</Badge>
      </Heading>
      <div className="participant-track">
        {roundNames.map((name, i) => (
          <div key={name} className={task?.round === i + 1 ? "current" : ""}>
            <span>{i + 1}</span>
            <strong>{name}</strong>
            {props.state.tasks
              .filter((t) => t.round === i + 1)
              .every((t) => t.status === "ended") && <Check size={16} />}
          </div>
        ))}
      </div>
      {!task ? (
        <div className="waiting-room">
          <span className="waiting-icon">
            <Radio size={37} />
          </span>
          <Badge tone="blue">You’re in</Badge>
          <h2>Your ideas are up next.</h2>
          <p>
            The organizer will release the first challenge here.
            <br />
            Keep this page open. It will update automatically.
          </p>
          <div className="waiting-details">
            <span>
              <ShieldCheck size={17} />
              Private team workspace
            </span>
            <span>
              <Clock3 size={17} />
              Official server timing
            </span>
          </div>
        </div>
      ) : task.round === 1 ? (
        <Quiz {...props} task={task} />
      ) : (
        <CreativeWorkspace {...props} task={task} key={task.id} />
      )}
    </>
  );
}

type QuizData = {
  questions: { id: number; text: string; options: string[]; points: number }[];
  answers: Record<number, { choice: number; saved: number }>;
};
export function Quiz({
  task,
  ...props
}: Common & { task: Task; user: User; connected: boolean }) {
  const { data, error, load } = useResource<QuizData>(
    "/quiz",
    { questions: [], answers: {} },
    task.status,
    15000,
  );
  const [index, setIndex] = useState(0);
  const [pending, setPending] = useState<Record<number, number>>(() => {
    try {
      return JSON.parse(readLocal("pp-quiz-" + props.user.team_id) || "{}");
    } catch {
      return {};
    }
  });
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<
    Record<number, { choice: number; saved: number }>
  >({});
  const [warn, setWarn] = useState("");
  const count = useRef(0);
  const active =
    task.status === "running" &&
    !!task.deadline &&
    Date.now() / 1000 + props.state.offset < task.deadline;
  const answers = { ...data.answers, ...saved };
  const question = data.questions[Math.min(index, data.questions.length - 1)];
  useEffect(() => {
    writeLocal("pp-quiz-" + props.user.team_id, JSON.stringify(pending));
  }, [pending, props.user.team_id]);
  const save = async (id: number, choice: number) => {
    setSaving(true);
    setSaveError("");
    setPending((p) => ({ ...p, [id]: choice }));
    try {
      const result = await api<{ choice: number; saved: number }>(
        "/quiz/" + id,
        send("PUT", { choice }),
      );
      setSaved((a) => ({ ...a, [id]: result }));
      setPending((p) => {
        const n = { ...p };
        delete n[id];
        return n;
      });
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };
  useEffect(() => {
    if (!active) return;
    let hidden = 0;
    let blurred = 0;
    const log = (type: string, duration?: number) => {
      void api("/incidents", send("POST", { type, duration })).catch(() => {});
      if (["hidden", "blur", "fullscreen_exit"].includes(type)) {
        count.current++;
        if (count.current >= props.state.integrity_threshold)
          setWarn(
            "Focus changes have been recorded for organizer review. Keep your attention on the quiz. A focus event does not automatically disqualify your team.",
          );
      }
    };
    const visibility = () => {
      if (document.hidden) {
        hidden = performance.now();
        log("hidden");
      } else {
        log(
          "visible",
          hidden ? (performance.now() - hidden) / 1000 : undefined,
        );
        hidden = 0;
      }
    };
    const blur = () => {
      blurred = performance.now();
      log("blur");
    };
    const focus = () => {
      log("focus", blurred ? (performance.now() - blurred) / 1000 : undefined);
      blurred = 0;
    };
    const full = () =>
      log(document.fullscreenElement ? "fullscreen_enter" : "fullscreen_exit");
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("blur", blur);
    window.addEventListener("focus", focus);
    document.addEventListener("fullscreenchange", full);
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("blur", blur);
      window.removeEventListener("focus", focus);
      document.removeEventListener("fullscreenchange", full);
    };
  }, [active, props.state.integrity_threshold]);
  const pendingIds = Object.keys(pending);
  return (
    <>
      <ResourceError error={error} retry={load} />
      <section className="quiz-shell">
        <div className="workspace-header">
          <div>
            <Badge tone="blue">Round 1 / AI knowledge</Badge>
            <h2>
              {task.status === "ended"
                ? "Quiz closed"
                : "A little knowledge goes a long way."}
            </h2>
            <p>
              {task.status === "ended"
                ? "Your saved answers are safely recorded. Wait for the next challenge."
                : "Choose the best answer. Every selection saves to the server."}
            </p>
          </div>
          <Timer state={props.state} task={task} />
        </div>
        {warn && (
          <div className="banner warning" role="alert">
            {warn}
          </div>
        )}
        {task.status === "paused" && (
          <div className="banner warning">
            The organizer has paused this task. Answers are temporarily locked.
          </div>
        )}
        {!active && task.status === "running" && (
          <div className="banner warning">
            The official deadline has passed. Your previously saved answers
            count; new answers are closed.
          </div>
        )}
        {question && (
          <div className="quiz-body">
            <aside className="question-navigator">
              <div className="section-title">
                <h3>Your progress</h3>
                <strong>
                  {Object.keys(answers).length}/{data.questions.length}
                </strong>
              </div>
              <progress
                value={Object.keys(answers).length}
                max={data.questions.length}
                aria-label="Questions answered"
              />
              <div className="question-grid">
                {data.questions.map((q, i) => (
                  <button
                    key={q.id}
                    className={
                      (i === index ? "current " : "") +
                      (answers[q.id] ? "answered " : "") +
                      (pending[q.id] !== undefined ? "unsaved" : "")
                    }
                    aria-label={`Question ${i + 1}, ${pending[q.id] !== undefined ? "unsaved" : answers[q.id] ? "answered" : "unanswered"}`}
                    aria-current={i === index ? "step" : undefined}
                    onClick={() => setIndex(i)}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
              <p>
                <span className="legend-square" />
                Saved answer
              </p>
              <p>Navigate freely until the official deadline.</p>
              <button
                className="text-button"
                onClick={() =>
                  void document.documentElement
                    .requestFullscreen()
                    .catch(() =>
                      props.notify(
                        "Fullscreen is unavailable in this browser.",
                      ),
                    )
                }
              >
                <Maximize2 size={15} />
                Focus view
              </button>
            </aside>
            <article className="quiz-question">
              <div className="question-meta">
                <span>
                  Question {index + 1} of {data.questions.length}
                </span>
                <Badge>
                  {question.points} {question.points === 1 ? "point" : "points"}
                </Badge>
              </div>
              <h3>{question.text}</h3>
              <fieldset className="answer-choices" disabled={!active || saving}>
                <legend className="sr-only">Choose your answer</legend>
                {question.options.map((option, i) => (
                  <label
                    key={i}
                    className={
                      "answer-option " +
                      ((pending[question.id] ??
                        answers[question.id]?.choice) === i
                        ? "selected"
                        : "")
                    }
                  >
                    <input
                      type="radio"
                      name={"q-" + question.id}
                      checked={
                        (pending[question.id] ??
                          answers[question.id]?.choice) === i
                      }
                      onChange={() => void save(question.id, i)}
                    />
                    <span className="answer-letter">
                      {String.fromCharCode(65 + i)}
                    </span>
                    <span>{option}</span>
                    <span className="answer-check">
                      {(pending[question.id] ??
                        answers[question.id]?.choice) === i && (
                        <Check size={17} />
                      )}
                    </span>
                  </label>
                ))}
              </fieldset>
              <div className="answer-footer">
                <span className="save-status" role="status">
                  {saving ? (
                    <>
                      <RefreshCw size={15} />
                      Saving answer…
                    </>
                  ) : pending[question.id] !== undefined ? (
                    <>
                      <Flag size={15} />
                      Not yet saved
                    </>
                  ) : answers[question.id] ? (
                    <>
                      <CheckCheck size={16} />
                      Saved at {shortTime(answers[question.id].saved)}
                    </>
                  ) : (
                    <>
                      <ShieldCheck size={16} />
                      Your answer saves automatically
                    </>
                  )}
                </span>
                <div>
                  <button
                    className="icon-button"
                    disabled={index === 0}
                    aria-label="Previous question"
                    onClick={() => setIndex((i) => i - 1)}
                  >
                    <ArrowLeft size={18} />
                  </button>
                  <button
                    className="button primary"
                    disabled={index === data.questions.length - 1}
                    onClick={() => setIndex((i) => i + 1)}
                  >
                    Next question
                    <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            </article>
          </div>
        )}
      </section>
      {(saveError || pendingIds.length > 0) && (
        <div className="banner warning" role="alert">
          <span>
            {saveError ||
              "You have unsaved answers from a previous connection. Retry before the deadline."}
          </span>
          <button
            className="button secondary"
            disabled={!active || saving}
            onClick={async () => {
              for (const id of pendingIds)
                await save(Number(id), pending[Number(id)]);
            }}
          >
            Retry unsaved answers ({pendingIds.length})
          </button>
        </div>
      )}
    </>
  );
}

type DraftFields = { prompt: string; link: string; rationale: string };
export function CreativeWorkspace({
  task,
  ...props
}: Common & { task: Task; user: User; connected: boolean }) {
  const [form, setForm] = useState<DraftFields>({
    prompt: "",
    link: "",
    rationale: "",
  });
  const [ready, setReady] = useState(false);
  const [savedDraft, setSavedDraft] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [evidence, setEvidence] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [receipt, setReceipt] = useState<Submission | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [err, setErr] = useState("");
  const key = useRef(crypto.randomUUID());
  const payload = useRef<FormData | null>(null);
  const active =
    task.status === "running" &&
    !!task.deadline &&
    Date.now() / 1000 + props.state.offset < task.deadline + task.grace;
  const draftKey = `pp-draft-${props.user.team_id}-${task.id}`;
  useEffect(() => {
    if (!props.connected) return;
    let cancelled = false;
    api<{ draft: DraftFields | null; submission: Submission | null }>(
      `/tasks/${task.id}/work`,
    )
      .then((w) => {
        if (cancelled) return;
        const local = readLocal(draftKey);
        let fields =
          w.draft ||
          (w.submission
            ? {
                prompt: w.submission.prompt,
                link: w.submission.link,
                rationale: w.submission.rationale,
              }
            : null);
        if (local) {
          try {
            fields = JSON.parse(local);
          } catch {}
        }
        if (fields) setForm(fields);
        setReceipt(w.submission);
        setErr("");
        setReady(true);
      })
      .catch((e) => setErr(e.message));
    return () => {
      cancelled = true;
    };
  }, [task.id, draftKey, props.connected]);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const u = URL.createObjectURL(file);
    setPreview(u);
    return () => URL.revokeObjectURL(u);
  }, [file]);
  useEffect(() => {
    if (!ready) return;
    const cached = writeLocal(draftKey, JSON.stringify(form));
    if (!active || !props.connected) return;
    setSavedDraft("Saving draft…");
    const t = setTimeout(() => {
      api(`/tasks/${task.id}/draft`, send("PUT", form))
        .then(() => setSavedDraft("Draft saved to server"))
        .catch(() =>
          setSavedDraft(
            cached
              ? "Draft kept on this device. Reconnect to sync."
              : "Draft kept in this open page. Reconnect before refreshing.",
          ),
        );
    }, 800);
    return () => clearTimeout(t);
  }, [form, ready, active, task.id, draftKey, props.connected]);
  const change = (k: keyof DraftFields, v: string) => {
    payload.current = null;
    key.current = crypto.randomUUID();
    setForm((f) => ({ ...f, [k]: v }));
  };
  return (
    <>
      <section className="creative-header">
        <div>
          <Badge tone="blue">
            Round {task.round} /{" "}
            {task.round === 2
              ? `Image ${task.id - 1} of ${props.state.tasks.filter((t) => t.round === 2).length}`
              : "Brand challenge"}
          </Badge>
          <h2>{task.title}</h2>
          <p>
            {task.status === "ended"
              ? "This challenge is closed. Your received work is preserved."
              : task.status === "paused"
                ? "Creation is paused. Your saved draft is preserved."
                : "Your next idea starts here."}
          </p>
        </div>
        <Timer task={task} state={props.state} />
      </section>
      <div className="creative-grid">
        <aside className="creative-brief">
          <span className="round-art-icon">
            {task.round === 2 ? (
              <ImageIcon size={28} />
            ) : (
              <WandSparkles size={28} />
            )}
          </span>
          <h3>
            {task.round === 2
              ? "Look closely. Create boldly."
              : "Meet your next brand."}
          </h3>
          <p className="preserve">{task.brief}</p>
          {task.requirements && (
            <>
              <h4>What your logo must include</h4>
              <p className="preserve">{task.requirements}</p>
            </>
          )}
          {task.round === 2 && (
            <div className="reference-note">
              <Monitor size={21} />
              <p>
                The reference is on the shared presentation screen. It is
                intentionally kept outside this workspace.
              </p>
            </div>
          )}
          <dl className="challenge-facts">
            <div>
              <dt>Creation period</dt>
              <dd>{task.duration / 60} minutes</dd>
            </div>
            <div>
              <dt>Submission grace</dt>
              <dd>{task.grace ? task.grace / 60 + " minutes" : "None"}</dd>
            </div>
            <div>
              <dt>Published attempt limit</dt>
              <dd>
                {task.attempt_limit} <span>(self reported)</span>
              </dd>
            </div>
            <div>
              <dt>Task ID</dt>
              <dd>PP-{String(task.id).padStart(2, "0")}</dd>
            </div>
          </dl>
          <div className="integration-note">
            <Badge tone="amber">Manual workflow active</Badge>
            <p>
              ChatGPT session capture is unavailable. Generation attempts are
              not independently tracked. No account credentials are collected.
            </p>
            <a
              className="button secondary wide"
              href="https://chatgpt.com/"
              target="_blank"
              rel="noreferrer"
            >
              Open your ChatGPT
              <ExternalLink size={15} />
            </a>
          </div>
          <h4>What the judges look for</h4>
          {task.rubric.map((r) => (
            <div className="criterion-row" key={r.name}>
              <span>{r.name}</span>
              <b>{r.weight}%</b>
            </div>
          ))}
        </aside>
        <section className="submission-workspace">
          <div className="section-title">
            <h3>Your final creation</h3>
            <Badge tone={receipt ? "success" : "neutral"}>
              {receipt ? "Submission received" : "Work in progress"}
            </Badge>
          </div>
          {receipt && (
            <div className="receipt">
              <CheckCheck size={23} />
              <div>
                <h4>Received. You’re on record.</h4>
                <p>
                  {dateTime(receipt.submitted)} · Revision {receipt.revision}
                  {receipt.late ? " · Grace period" : ""}
                </p>
                <span>Receipt {receipt.receipt}</span>
                {receipt.evidence_flag && (
                  <p>
                    Conversation evidence is missing and flagged for judge
                    review. Your image and prompt are accepted.
                  </p>
                )}
              </div>
            </div>
          )}
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setErr("");
              if (!file) {
                setErr("Choose your final image before submitting.");
                return;
              }
              if (!payload.current) {
                const d = new FormData();
                d.append("image", file);
                if (evidence) d.append("evidence", evidence);
                d.append("prompt", form.prompt);
                d.append("link", form.link);
                d.append("rationale", form.rationale);
                d.append("request_key", key.current);
                payload.current = d;
              }
              props.confirm({
                title: receipt
                  ? "Replace your submitted creation?"
                  : "Submit your final creation?",
                description:
                  "The server will confirm acceptance and issue your receipt. Missing conversation evidence is flagged for review and does not block an image and prompt.",
                label: receipt ? "Replace submission" : "Confirm submission",
                action: async () => {
                  setBusy(true);
                  setProgress(0);
                  try {
                    const r = await upload<Submission>(
                      `/tasks/${task.id}/submit`,
                      payload.current!,
                      setProgress,
                    );
                    setReceipt(r);
                    setErr("");
                    props.notify("Submission received. Your receipt is ready.");
                    props.refresh();
                  } catch (e) {
                    setErr((e as Error).message);
                    throw e;
                  } finally {
                    setBusy(false);
                  }
                },
              });
            }}
          >
            <fieldset disabled={!active || busy || !ready || receipt?.approved}>
              <label className={"image-upload " + (preview ? "has-image" : "")}>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  aria-label="Final generated image"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    payload.current = null;
                    key.current = crypto.randomUUID();
                  }}
                />
                {preview ? (
                  <img src={preview} alt="Selected image preview" />
                ) : receipt ? (
                  <img
                    src={"/api/assets/" + receipt.asset_id}
                    alt="Previously submitted creation"
                  />
                ) : (
                  <>
                    <span className="upload-icon">
                      <Upload size={25} />
                    </span>
                    <strong>Give your idea the spotlight.</strong>
                    <span>Choose your final image to upload</span>
                    <small>PNG, JPEG, or WebP · Up to 12 MB</small>
                  </>
                )}
                <span className="upload-caption">
                  {file
                    ? file.name
                    : receipt
                      ? "Choose a replacement image"
                      : "Browse files"}
                </span>
              </label>
              <label>
                Final prompt <span className="required">Required</span>
                <textarea
                  rows={5}
                  required
                  maxLength={20000}
                  value={form.prompt}
                  onChange={(e) => change("prompt", e.target.value)}
                  placeholder="Paste the final prompt used to create your image. Be specific about your creative choices."
                />
              </label>
              <label>
                ChatGPT conversation link{" "}
                <span className="muted">Optional</span>
                <input
                  type="url"
                  value={form.link}
                  maxLength={2000}
                  onChange={(e) => change("link", e.target.value)}
                  placeholder="https://chatgpt.com/share/…"
                />
                <small className="field-hint">
                  A missing or inaccessible link is flagged for review. Your
                  image and prompt can still be accepted.
                </small>
              </label>
              <label>
                Evidence screenshot <span className="muted">Optional</span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => {
                    setEvidence(e.target.files?.[0] || null);
                    payload.current = null;
                    key.current = crypto.randomUUID();
                  }}
                />
                <small className="field-hint">
                  Include only this challenge’s relevant prompts and outputs. Up
                  to 12 MB.
                </small>
              </label>
              {task.round === 3 && (
                <label>
                  Design rationale <span className="muted">Optional</span>
                  <textarea
                    rows={3}
                    maxLength={10000}
                    value={form.rationale}
                    onChange={(e) => change("rationale", e.target.value)}
                    placeholder="Explain how your logo answers the brief."
                  />
                </label>
              )}
            </fieldset>
            <div className="form-error" role="alert">
              {err}
            </div>
            {busy && (
              <div className="upload-progress">
                <progress max={100} value={progress} />
                <span>
                  {progress < 100
                    ? `Uploading ${progress}%`
                    : "Upload complete. Waiting for server confirmation…"}
                </span>
              </div>
            )}
            <div className="submission-footer">
              <span className="save-status" role="status">
                <ShieldCheck size={15} />
                {savedDraft || "Your draft stays private"}
              </span>
              <button
                className="button primary"
                disabled={!active || busy || !ready || receipt?.approved}
              >
                {busy
                  ? "Confirming…"
                  : receipt
                    ? "Replace submission"
                    : "Submit creation"}
                <ArrowRight size={16} />
              </button>
            </div>
            {!active && (
              <p className="field-hint">
                {task.status === "paused"
                  ? "The organizer has paused submissions."
                  : task.status === "ended"
                    ? "This task is closed."
                    : "The official submission deadline has passed."}
              </p>
            )}
          </form>
        </section>
      </div>
    </>
  );
}

export function SubmissionHistory({ state, ...props }: Common) {
  const { data, error, load } = useResource<Submission[]>("/submissions", []);
  return (
    <>
      <Heading
        title="Your submissions"
        description="Your creative work, with a receipt for every accepted entry."
      />
      <ResourceError error={error} retry={load} />
      {data.length ? (
        <div className="submission-gallery">
          {data.map((s) => (
            <article className="submission-tile" key={s.id}>
              <img
                src={"/api/assets/" + s.asset_id}
                alt={`Submitted creation for ${state.tasks.find((t) => t.id === s.task_id)?.title}`}
              />
              <div>
                <Badge tone={s.approved ? "success" : "blue"}>
                  {s.status === "rejected"
                    ? "Rejected"
                    : s.approved
                      ? "Approved"
                      : "Received"}
                </Badge>
                <h2>{state.tasks.find((t) => t.id === s.task_id)?.title}</h2>
                <p>
                  {dateTime(s.submitted)} · Revision {s.revision}
                </p>
                <details>
                  <summary>Prompt & receipt</summary>
                  <p className="preserve">{s.prompt}</p>
                  <small>Receipt: {s.receipt}</small>
                </details>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty icon={ImageIcon} title="Your first creation belongs here">
          Accepted creative submissions will appear here with their prompt,
          timestamp, and receipt.
        </Empty>
      )}
    </>
  );
}
