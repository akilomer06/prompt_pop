import { api, send, upload } from "@/api";
import { Badge, Heading, Timer } from "@/components/ui";
import { roundNames } from "@/lib/helpers";
import type { Common, EventState, Task } from "@/types";
import { BookOpen, Pause, Play, Plus, Square, Upload } from "lucide-react";
import { useEffect, useState } from "react";
export function TaskControls({
  state,
  task,
  confirm,
  refresh,
  notify,
}: {
  state: EventState;
  task: Task;
  confirm: Common["confirm"];
  refresh: () => void;
  notify: Common["notify"];
}) {
  const action = (name: string, label: string, danger = false) =>
    confirm({
      title: label + "?",
      description:
        name === "start"
          ? `This reveals “${task.title}” to every team and starts the official ${task.duration / 60}-minute timer.`
          : name === "end"
            ? "This closes submissions immediately for every team. This task cannot be reopened."
            : "The server will synchronize this change for every connected team.",
      label,
      danger,
      action: async () => {
        await api(
          "/admin/control",
          send("POST", { action: name, task_id: task.id }),
        );
        notify(label + " confirmed.");
        refresh();
      },
    });
  return (
    <div className="task-controls">
      {task.status === "pending" && task.id === state.current + 1 && (
        <button
          className="button primary"
          onClick={() => action("start", "Release & start task")}
        >
          <Play size={16} />
          Release & start task
        </button>
      )}
      {task.status === "running" && (
        <>
          <button
            className="button secondary"
            onClick={() => action("pause", "Pause task")}
          >
            <Pause size={16} />
            Pause task
          </button>
          <button
            className="button danger-quiet"
            onClick={() => action("end", "Close task", true)}
          >
            <Square size={14} />
            Close task
          </button>
        </>
      )}
      {task.status === "paused" && (
        <>
          <button
            className="button primary"
            onClick={() => action("resume", "Resume task")}
          >
            <Play size={16} />
            Resume task
          </button>
          <button
            className="button danger-quiet"
            onClick={() => action("end", "Close task", true)}
          >
            Close task
          </button>
        </>
      )}
    </div>
  );
}

export function Rounds(props: Common) {
  const { state, notify, refresh } = props;
  const [selected, setSelected] = useState(state.current || 1);
  const task = state.tasks.find((t) => t.id === selected)!;
  return (
    <>
      <Heading
        title="Rounds & content"
        description="Prepare every challenge. Release each one with confidence."
      />
      <div className="round-editor">
        <nav className="task-nav" aria-label="Competition tasks">
          {roundNames.map((name, i) => (
            <div key={name}>
              <h2>
                Round {i + 1}
                <small>{name}</small>
              </h2>
              {state.tasks
                .filter((t) => t.round === i + 1)
                .map((t) => (
                  <button
                    className={selected === t.id ? "selected" : ""}
                    key={t.id}
                    onClick={() => setSelected(t.id)}
                  >
                    <span>{t.title}</span>
                    <Badge
                      tone={
                        t.status === "running"
                          ? "blue"
                          : t.status === "ended"
                            ? "success"
                            : "neutral"
                      }
                    >
                      {t.status}
                    </Badge>
                  </button>
                ))}
            </div>
          ))}
        </nav>
        <div className="round-editor-content">
          <div className="task-summary">
            <div>
              <Badge tone="blue">Round {task.round}</Badge>
              <h2>{task.title}</h2>
              <p>
                {task.status === "pending"
                  ? "Only unreleased content can be edited. Review before starting."
                  : "Released content is locked to preserve fairness."}
              </p>
            </div>
            <Timer task={task} state={state} />
          </div>
          <TaskControls {...props} task={task} />
          <TaskEditor
            key={`${task.id}-${task.status}`}
            task={task}
            notify={notify}
            refresh={refresh}
          />
          {task.round === 1 && (
            <QuizEditor editable={task.status === "pending"} notify={notify} />
          )}{" "}
          {["running", "paused"].includes(task.status) && (
            <TimeAdjustment {...props} task={task} />
          )}
        </div>
      </div>
    </>
  );
}
export function TaskEditor({
  task,
  notify,
  refresh,
}: {
  task: Task;
  notify: Common["notify"];
  refresh: () => void;
}) {
  const [form, setForm] = useState({
    ...task,
    brief: task.brief || "",
    requirements: task.requirements || "",
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const update = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));
  const locked = task.status !== "pending";
  return (
    <form
      className="task-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setErr("");
        try {
          await api(`/admin/tasks/${task.id}`, send("PUT", form));
          notify("Challenge settings saved.");
          refresh();
        } catch (e) {
          setErr((e as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <fieldset disabled={locked || busy}>
        <div className="form-section-heading">
          <h3>Challenge details</h3>
          <span>{locked ? "Content locked" : "Organizer view"}</span>
        </div>
        <label>
          Challenge title
          <input
            value={form.title}
            required
            maxLength={150}
            onChange={(e) => update("title", e.target.value)}
          />
        </label>
        <div className="form-grid">
          <label>
            Creation time (seconds)
            <input
              type="number"
              min={30}
              max={14400}
              required
              value={form.duration}
              onChange={(e) => update("duration", Number(e.target.value))}
            />
          </label>
          <label>
            Submission grace (seconds)
            <input
              type="number"
              min={0}
              max={600}
              required
              disabled={task.round === 1}
              value={task.round === 1 ? 0 : form.grace}
              onChange={(e) => update("grace", Number(e.target.value))}
            />
          </label>
        </div>
        <label>
          {task.round === 3
            ? "Case study / brand brief"
            : "Participant instructions"}
          <textarea
            rows={5}
            maxLength={20000}
            value={form.brief}
            onChange={(e) => update("brief", e.target.value)}
            placeholder={
              task.round === 3
                ? "Write the business context, audience, brand name, and creative objective."
                : ""
            }
          />
        </label>
        {task.round === 3 && (
          <label>
            Mandatory brand requirements
            <textarea
              rows={3}
              maxLength={10000}
              value={form.requirements}
              onChange={(e) => update("requirements", e.target.value)}
              placeholder="Required text, colors, deliverables, and any constraints"
            />
          </label>
        )}
        {task.round !== 1 && (
          <>
            <label>
              Published generation attempt limit
              <input
                type="number"
                min={1}
                max={100}
                required
                value={form.attempt_limit}
                onChange={(e) =>
                  update("attempt_limit", Number(e.target.value))
                }
              />
              <small className="field-hint">
                Guidance for teams. Technical enforcement is unavailable because
                ChatGPT generation events are not verified.
              </small>
            </label>
            <h3>Scoring rubric</h3>
            <p className="muted">
              Criterion weights must total 100. Judges score each from 0 to 100.
            </p>
            <div className="rubric-editor">
              {form.rubric.map((r, i) => (
                <div key={i}>
                  <label>
                    Criterion {i + 1}
                    <input
                      value={r.name}
                      required
                      maxLength={100}
                      onChange={(e) =>
                        update(
                          "rubric",
                          form.rubric.map((v, j) =>
                            j === i ? { ...v, name: e.target.value } : v,
                          ),
                        )
                      }
                    />
                  </label>
                  <label>
                    Weight %
                    <input
                      type="number"
                      value={r.weight}
                      min={1}
                      max={100}
                      required
                      onChange={(e) =>
                        update(
                          "rubric",
                          form.rubric.map((v, j) =>
                            j === i
                              ? { ...v, weight: Number(e.target.value) }
                              : v,
                          ),
                        )
                      }
                    />
                  </label>
                </div>
              ))}
            </div>
          </>
        )}
      </fieldset>
      <div role="alert" className="form-error">
        {err}
      </div>
      {!locked && (
        <button className="button primary" disabled={busy}>
          {busy ? "Saving…" : "Save challenge"}
        </button>
      )}
      {task.round === 2 && (
        <section className="private-reference">
          <h3>Private reference image</h3>
          <p>
            Shown only to organizers and judges. Present it on the shared event
            screen; participant APIs never expose this asset.
          </p>
          {task.reference_id && (
            <img
              src={"/api/assets/" + task.reference_id}
              alt="Official private reference"
            />
          )}
          {!locked && (
            <label className="file-field">
              <Upload size={20} />
              Choose PNG, JPEG, or WebP
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const d = new FormData();
                  d.append("image", file);
                  setBusy(true);
                  try {
                    await upload(
                      `/admin/tasks/${task.id}/reference`,
                      d,
                      () => {},
                    );
                    notify("Private reference saved.");
                    refresh();
                  } catch (e) {
                    setErr((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              />
            </label>
          )}
        </section>
      )}
      {task.round === 3 && (
        <section className="brief-preview">
          <Badge tone="blue">Participant preview</Badge>
          <h3>{form.title}</h3>
          <p className="preserve">
            {form.brief ||
              "Add a case study above to preview the participant brief."}
          </p>
          {form.requirements && (
            <>
              <h4>Requirements</h4>
              <p className="preserve">{form.requirements}</p>
            </>
          )}
        </section>
      )}
    </form>
  );
}

export function QuizEditor({
  editable,
  notify,
}: {
  editable: boolean;
  notify: Common["notify"];
}) {
  const [open, setOpen] = useState(false);
  const [questions, setQuestions] = useState<
    {
      id?: number;
      text: string;
      options: string[];
      correct: number;
      points: number;
    }[]
  >([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<typeof questions>("/admin/questions")
      .then(setQuestions)
      .catch((e) => setErr(e.message));
  }, []);
  const setQ = (i: number, k: string, v: unknown) =>
    setQuestions((q) => q.map((a, j) => (i === j ? { ...a, [k]: v } : a)));
  return (
    <section className="question-editor">
      <button
        className="disclosure"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <span>
          <BookOpen size={19} />
          Question bank <Badge>{questions.length} questions</Badge>
        </span>
        <Plus size={18} />
      </button>
      {open && (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setErr("");
            try {
              await api("/admin/questions", send("PUT", { questions }));
              notify("Quiz bank saved.");
            } catch (e) {
              setErr((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="banner">
            The included bank is an editable starting set. Review and approve
            every question before your event.
          </div>
          <fieldset disabled={!editable || busy}>
            {questions.map((q, i) => (
              <div className="question-config" key={i}>
                <label>
                  Question {i + 1}
                  <textarea
                    rows={2}
                    value={q.text}
                    required
                    minLength={5}
                    onChange={(e) => setQ(i, "text", e.target.value)}
                  />
                </label>
                {q.options.map((o, j) => (
                  <label key={j} className="option-edit">
                    <input
                      type="radio"
                      name={"correct-" + i}
                      checked={q.correct === j}
                      onChange={() => setQ(i, "correct", j)}
                      aria-label={`Correct answer ${String.fromCharCode(65 + j)} for question ${i + 1}`}
                    />
                    <input
                      value={o}
                      required
                      aria-label={`Option ${String.fromCharCode(65 + j)} for question ${i + 1}`}
                      onChange={(e) =>
                        setQ(
                          i,
                          "options",
                          q.options.map((a, k) =>
                            k === j ? e.target.value : a,
                          ),
                        )
                      }
                    />
                  </label>
                ))}
                <label>
                  Points
                  <input
                    type="number"
                    required
                    min={0.1}
                    max={100}
                    step={0.1}
                    value={q.points}
                    onChange={(e) => setQ(i, "points", Number(e.target.value))}
                  />
                </label>
                <button
                  type="button"
                  className="text-button danger-text"
                  onClick={() =>
                    setQuestions((v) => v.filter((_, j) => j !== i))
                  }
                >
                  Remove question
                </button>
              </div>
            ))}
            <button
              type="button"
              className="button secondary"
              onClick={() =>
                setQuestions((q) => [
                  ...q,
                  {
                    text: "",
                    options: ["", "", "", ""],
                    correct: 0,
                    points: 1,
                  },
                ])
              }
            >
              <Plus size={16} />
              Add question
            </button>
          </fieldset>
          <div role="alert" className="form-error">
            {err}
          </div>
          {editable && (
            <button className="button primary" disabled={busy}>
              Save question bank
            </button>
          )}
        </form>
      )}
    </section>
  );
}

export function TimeAdjustment({ task, ...props }: Common & { task: Task }) {
  return (
    <form
      className="time-adjustment"
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        props.confirm({
          title: "Add official time?",
          description: `Add ${f.get("seconds")} seconds for every team. The reason and adjustment will be recorded in the activity log.`,
          label: "Add time",
          action: async () => {
            await api(
              "/admin/control",
              send("POST", {
                action: "extend",
                task_id: task.id,
                seconds: Number(f.get("seconds")),
                reason: f.get("reason"),
              }),
            );
            props.refresh();
            props.notify("Official time adjusted for every team.");
          },
        });
      }}
    >
      <h3>Fairness adjustment</h3>
      <div className="form-grid">
        <label>
          Additional seconds
          <input
            name="seconds"
            type="number"
            min={1}
            max={3600}
            defaultValue={60}
            required
          />
        </label>
        <label>
          Reason for the audit log
          <input
            name="reason"
            maxLength={2000}
            required
            placeholder="Explain the event-wide adjustment"
          />
        </label>
      </div>
      <button className="button secondary">Review time adjustment</button>
    </form>
  );
}
