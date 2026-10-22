import { api, send } from "@/api";
import { Badge, Empty, Heading, ResourceError } from "@/components/ui";
import { dateTime, human, shortTime } from "@/lib/helpers";
import { useResource } from "@/lib/useResource";
import type { Common, Team } from "@/types";
import { Flag, ShieldCheck } from "lucide-react";
type IntegrityIncident = {
  id: string;
  team_id: string;
  type: string;
  timestamp: number;
  duration: number | null;
  reviewed: boolean;
  notes: string;
};
export function Incidents(props: Common) {
  const incidents = useResource<IntegrityIncident[]>("/admin/incidents", []);
  const teams = useResource<Team[]>("/admin/teams", []);
  return (
    <>
      <Heading
        title="Integrity review"
        description="Context before conclusions. Review events with human judgment."
      />
      <div className="banner">
        <ShieldCheck size={18} />
        Focus and fullscreen events are signals for review. A website cannot
        lock the operating system, and a single event never automatically
        disqualifies a team.
      </div>
      <ResourceError error={incidents.error} retry={incidents.load} />
      <section className="panel">
        {incidents.data.length ? (
          <div className="incident-list">
            {incidents.data.map((i) => (
              <article key={i.id}>
                <span className="incident-icon">
                  <Flag size={19} />
                </span>
                <div>
                  <h3>
                    {teams.data.find((t) => t.id === i.team_id)?.name || "Team"}{" "}
                    <Badge tone={i.reviewed ? "success" : "amber"}>
                      {i.reviewed ? "Reviewed" : "Needs context"}
                    </Badge>
                  </h3>
                  <p>
                    {human(i.type)} · {dateTime(i.timestamp)}
                    {i.duration !== null
                      ? ` · ${i.duration.toFixed(1)} seconds`
                      : ""}
                  </p>
                  {i.reviewed ? (
                    <p className="preserve">
                      {i.notes || "Reviewed without additional notes."}
                    </p>
                  ) : (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        const data = new FormData(e.currentTarget);
                        void api(
                          "/admin/incidents/" + i.id,
                          send("PUT", { notes: data.get("notes") }),
                        )
                          .then(() => {
                            void incidents.load();
                            props.notify("Incident review recorded.");
                          })
                          .catch((e) => props.notify(e.message));
                      }}
                    >
                      <label>
                        <span className="sr-only">
                          Review notes for {human(i.type)} at{" "}
                          {shortTime(i.timestamp)}
                        </span>
                        <input
                          name="notes"
                          maxLength={2000}
                          placeholder="Add context or a review note"
                        />
                      </label>
                      <button className="button secondary">
                        Mark reviewed
                      </button>
                    </form>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty icon={ShieldCheck} title="Nothing to review yet">
            Quiz focus and fullscreen events will appear here with their
            timestamps and available durations.
          </Empty>
        )}
      </section>
    </>
  );
}
