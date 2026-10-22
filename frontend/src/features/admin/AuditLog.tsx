import { Empty, Heading, ResourceError } from "@/components/ui";
import { dateTime, human } from "@/lib/helpers";
import { useResource } from "@/lib/useResource";
import type { Common } from "@/types";
import { Activity, ChevronRight } from "lucide-react";
export function AuditLog(props: Common) {
  const logs = useResource<
    {
      id: string;
      actor: string;
      action: string;
      timestamp: number;
      details: Record<string, unknown>;
    }[]
  >("/admin/audit", []);
  return (
    <>
      <Heading
        title="Activity log"
        description="Every consequential action leaves a clear record."
      />
      <ResourceError error={logs.error} retry={logs.load} />
      <div className="panel audit-panel">
        {logs.data.length ? (
          logs.data.map((l) => (
            <details key={l.id}>
              <summary>
                <span className="audit-icon">
                  <Activity size={16} />
                </span>
                <strong>{human(l.action)}</strong>
                <span>{l.actor}</span>
                <time>{dateTime(l.timestamp)}</time>
                <ChevronRight size={15} />
              </summary>
              <pre>{JSON.stringify(l.details, null, 2)}</pre>
            </details>
          ))
        ) : (
          <Empty icon={Activity} title="A clean start">
            Team creation, task controls, time adjustments, submissions, and
            scoring decisions are recorded here.
          </Empty>
        )}
      </div>
    </>
  );
}
