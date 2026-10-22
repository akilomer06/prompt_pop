import { api, send } from "@/api";
import { Badge, Empty, Heading, ResourceError } from "@/components/ui";
import { useResource } from "@/lib/useResource";
import type { Common, Team } from "@/types";
import { Plus, Search, ShieldCheck, Users, X } from "lucide-react";
import { useState } from "react";
export function Teams(props: Common & { refreshKey: number }) {
  const teams = useResource<Team[]>("/admin/teams", [], props.refreshKey);
  const [open, setOpen] = useState(false);
  const [creds, setCreds] = useState<{
    username: string;
    access_code: string;
  } | null>(null);
  const [query, setQuery] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const displayed = teams.data.filter((t) =>
    (t.name + t.username).toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <>
      <Heading
        title="Teams"
        description="A place for every team. Private access for every participant."
      >
        <button className="button primary" onClick={() => setOpen(!open)}>
          <Plus size={17} />
          Register team
        </button>
      </Heading>
      <ResourceError error={teams.error} retry={teams.load} />
      {creds && (
        <section className="credentials">
          <div>
            <ShieldCheck size={25} />
            <h2>Team access is ready</h2>
            <p>
              Copy these details now and share them privately with the team. The
              access code is shown only once.
            </p>
          </div>
          <dl>
            <dt>Account</dt>
            <dd>{creds.username}</dd>
            <dt>Access code</dt>
            <dd>{creds.access_code}</dd>
          </dl>
          <button
            className="button secondary"
            onClick={() => {
              void navigator.clipboard
                .writeText(
                  `Account: ${creds.username}\nAccess code: ${creds.access_code}`,
                )
                .then(() => props.notify("Team access copied."))
                .catch(() =>
                  props.notify("Select and copy the access details above."),
                );
            }}
          >
            Copy access details
          </button>
          <button
            className="icon-button"
            aria-label="Hide access details"
            onClick={() => setCreds(null)}
          >
            <X />
          </button>
        </section>
      )}
      {open && (
        <form
          className="panel inline-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            setBusy(true);
            setErr("");
            try {
              const c = await api<{ username: string; access_code: string }>(
                "/admin/teams",
                send("POST", {
                  name: f.get("name"),
                  members: String(f.get("members"))
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                }),
              );
              setCreds(c);
              setOpen(false);
              void teams.load();
              props.refresh();
            } catch (e) {
              setErr((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <h2>Register a team</h2>
          <div className="form-grid">
            <label>
              Team name
              <input
                name="name"
                required
                minLength={2}
                maxLength={100}
                placeholder="e.g. Studio North"
              />
            </label>
            <label>
              Members <span className="muted">(comma separated, optional)</span>
              <input name="members" placeholder="Member names" />
            </label>
          </div>
          <div className="form-error" role="alert">
            {err}
          </div>
          <button className="button primary" disabled={busy}>
            {busy ? "Creating…" : "Create team & access code"}
          </button>
        </form>
      )}
      <div className="panel">
        <div className="panel-header">
          <h2>
            Team roster <Badge>{teams.data.length}</Badge>
          </h2>
          <label className="search-field">
            <Search size={17} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Find a team"
              aria-label="Find a team"
            />
          </label>
        </div>
        {displayed.length ? (
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
                  <th>Account</th>
                  <th>Members</th>
                  <th>Connection</th>
                  <th>Access</th>
                  <th>Manage</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map((t, i) => (
                  <tr key={t.id}>
                    <td>
                      <span className="team-name">
                        <span className={"team-avatar color-" + (i % 4)}>
                          {t.name.slice(0, 2).toUpperCase()}
                        </span>
                        <strong>{t.name}</strong>
                      </span>
                    </td>
                    <td className="mono">{t.username}</td>
                    <td>{t.members.join(", ") || "Not specified"}</td>
                    <td>
                      <Badge tone={t.online ? "success" : "neutral"}>
                        {t.online ? "Online" : "Offline"}
                      </Badge>
                    </td>
                    <td>
                      <Badge tone={t.active ? "blue" : "amber"}>
                        {t.active ? "Active" : "Disabled"}
                      </Badge>
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          className="text-button"
                          onClick={() =>
                            props.confirm({
                              title: "Reset team access?",
                              description:
                                "This signs out the team and replaces its access code. Share the new code privately.",
                              label: "Reset access",
                              action: async () => {
                                setCreds(
                                  await api(
                                    `/admin/teams/${t.id}`,
                                    send("POST", { action: "reset" }),
                                  ),
                                );
                                void teams.load();
                              },
                            })
                          }
                        >
                          Reset
                        </button>
                        <button
                          className="text-button"
                          onClick={() =>
                            props.confirm({
                              title:
                                (t.active ? "Disable" : "Enable") +
                                " team access?",
                              description: t.active
                                ? "The team will be signed out. Existing work remains safely stored."
                                : "The team can sign in using its current access code.",
                              label: t.active
                                ? "Disable access"
                                : "Enable access",
                              danger: t.active,
                              action: async () => {
                                await api(
                                  `/admin/teams/${t.id}`,
                                  send("POST", {
                                    action: t.active ? "disable" : "enable",
                                  }),
                                );
                                void teams.load();
                              },
                            })
                          }
                        >
                          {t.active ? "Disable" : "Enable"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            icon={Users}
            title={query ? "No matching teams" : "The arena is waiting"}
          >
            {query
              ? "Try another team name or account."
              : "Register teams to generate their individual sign-in details. Team size is up to you."}
          </Empty>
        )}
      </div>
    </>
  );
}
