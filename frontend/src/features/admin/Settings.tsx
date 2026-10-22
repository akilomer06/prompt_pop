import { api, send } from "@/api";
import { Badge, Heading } from "@/components/ui";
import { roundNames } from "@/lib/helpers";
import type { Common } from "@/types";
import { useState } from "react";
export function Settings(props: Common) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  return (
    <>
      <Heading
        title="Event settings"
        description="Set the rules before the first idea takes shape."
      />
      <form
        className="panel settings-form"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setBusy(true);
          setErr("");
          try {
            await api(
              "/admin/settings",
              send("PUT", {
                title: f.get("title"),
                weights: [1, 2, 3].map((n) => Number(f.get("weight-" + n))),
                tie_break: f.get("tie_break"),
                integrity_threshold: Number(f.get("integrity_threshold")),
                image_task_count: Number(f.get("image_task_count")),
              }),
            );
            props.notify(
              "Event settings saved. Any published results are now private for review.",
            );
            props.refresh();
          } catch (e) {
            setErr((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2>Competition identity</h2>
        <label>
          Event name
          <input
            name="title"
            defaultValue={props.state.title}
            required
            minLength={2}
            maxLength={100}
          />
        </label>
        <h2>Challenge structure</h2>
        <label>
          Image recreation challenges
          <input
            name="image_task_count"
            type="number"
            min={1}
            max={20}
            defaultValue={props.state.tasks.filter((t) => t.round === 2).length}
            required
          />
          <small className="field-hint">
            Change before the event starts or assets are uploaded. Challenge
            titles are regenerated; durations and rubrics carry forward.
          </small>
        </label>
        <h2>Round weighting</h2>
        <p>
          Weights must total 100. Each round score is normalized to 100 before
          applying these percentages. The image round averages all configured
          challenges.
        </p>
        <div className="three-fields">
          {roundNames.map((n, i) => (
            <label key={n}>
              {n} %
              <input
                name={"weight-" + (i + 1)}
                type="number"
                min={0}
                max={100}
                step={0.1}
                defaultValue={props.state.weights[i]}
                required
              />
            </label>
          ))}
        </div>
        <label>
          Tie-break rule
          <select name="tie_break" defaultValue={props.state.tie_break}>
            <option value="quiz">Higher AI quiz score, then shared rank</option>
            <option value="logo">Higher logo score, then shared rank</option>
            <option value="shared">Shared rank for equal totals</option>
          </select>
        </label>
        <h2>Integrity monitoring</h2>
        <label>
          Focus-event warning threshold
          <input
            name="integrity_threshold"
            type="number"
            min={1}
            max={100}
            required
            defaultValue={props.state.integrity_threshold}
          />
          <small className="field-hint">
            A warning threshold, not an automatic penalty or disqualification.
          </small>
        </label>
        <div className="form-error" role="alert">
          {err}
        </div>
        <button className="button primary" disabled={busy}>
          {busy ? "Saving…" : "Save event settings"}
        </button>
        <section className="integration-settings">
          <h2>ChatGPT & evaluation</h2>
          <Badge tone="amber">Manual fallback ready</Badge>
          <p>{props.state.integration.reason}</p>
          <p>
            Authorized vision evaluator:{" "}
            <strong>
              {props.state.integration.evaluator_configured
                ? "Configured"
                : "Not configured"}
            </strong>
            . Evaluation credentials are configured on the server. Judges can
            run the entire event without an evaluator.
          </p>
        </section>
      </form>
    </>
  );
}
