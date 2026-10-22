import { api, send } from "@/api";
import { Badge, Empty, Heading, ResourceError } from "@/components/ui";
import { human, roundNames } from "@/lib/helpers";
import { useResource } from "@/lib/useResource";
import type { Common, Ranking } from "@/types";
import { ArrowDownToLine, Trophy } from "lucide-react";
export function Leaderboard(props: Common & { admin: boolean }) {
  const result = useResource<{ published: boolean; rows: Ranking[] }>(
    "/leaderboard",
    { published: false, rows: [] },
    props.state.published,
  );
  return (
    <>
      <Heading
        title="Leaderboard"
        description={
          props.admin
            ? "Review the standings. Publish when every decision is final."
            : "Every round counts. Follow the competition standings."
        }
      >
        {props.admin && (
          <>
            <a
              className="button secondary"
              href="/api/admin/export?kind=results"
            >
              <ArrowDownToLine size={16} />
              Export results
            </a>
            <button
              className="button primary"
              onClick={() =>
                props.confirm({
                  title: props.state.published
                    ? "Unpublish final results?"
                    : "Publish final results?",
                  description: props.state.published
                    ? "Teams will no longer see the standings until you publish again."
                    : "All tasks must be closed and every received submission approved. Published results become visible to every team.",
                  label: props.state.published
                    ? "Unpublish results"
                    : "Publish results",
                  action: async () => {
                    await api(
                      "/admin/publish",
                      send("POST", { published: !props.state.published }),
                    );
                    props.refresh();
                    void result.load();
                    props.notify("Result visibility updated.");
                  },
                })
              }
            >
              <Trophy size={16} />
              {props.state.published ? "Unpublish results" : "Publish results"}
            </button>
          </>
        )}
      </Heading>
      <ResourceError error={result.error} retry={result.load} />
      <div className="leaderboard-banner">
        <Trophy size={29} />
        <div>
          <h2>
            {result.data.published
              ? "The results are in."
              : "The story is still being written."}
          </h2>
          <p>
            {props.admin
              ? "Only approved creative scores and closed quiz results count. Missing work receives zero."
              : "Final rankings appear here when the organizer publishes the results."}
          </p>
        </div>
        <Badge tone={result.data.published ? "success" : "blue"}>
          {result.data.published
            ? "Published"
            : props.admin
              ? "Private preview"
              : "Awaiting results"}
        </Badge>
      </div>
      {(props.admin || result.data.published) && (
        <div className="weight-key">
          {roundNames.map((n, i) => (
            <span key={n}>
              {n}
              <strong>{props.state.weights[i]}%</strong>
            </span>
          ))}
          <span>
            Tie-break<strong>{human(props.state.tie_break)}</strong>
          </span>
        </div>
      )}
      {result.data.rows.length ? (
        <section className="panel ranking-panel">
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Competition data table"
          >
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Team</th>
                  <th>AI knowledge</th>
                  <th>Image recreation</th>
                  <th>Logo design</th>
                  <th>Final score</th>
                </tr>
              </thead>
              <tbody>
                {result.data.rows.map((r) => (
                  <tr key={r.team_id}>
                    <td>
                      <span className={"rank " + (r.rank === 1 ? "first" : "")}>
                        {String(r.rank).padStart(2, "0")}
                      </span>
                    </td>
                    <td>
                      <strong>{r.team}</strong>
                    </td>
                    {r.rounds.map((v, i) => (
                      <td key={i}>
                        {v.toFixed(2)}
                        <span className="muted"> / 100</span>
                      </td>
                    ))}
                    <td className="final-score">{r.total.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <Empty
          icon={Trophy}
          title={
            props.admin
              ? "The standings start with your teams"
              : "Your moment is coming"
          }
        >
          {props.admin
            ? "Register teams and complete the rounds to build the final rankings."
            : "The organizer will publish the final leaderboard after judging is complete."}
        </Empty>
      )}
    </>
  );
}
