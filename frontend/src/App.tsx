import { api, ApiError } from "@/api";
import { Brand, Confirm, Icon } from "@/components/ui";
import { AuditLog } from "@/features/admin/AuditLog";
import { ControlRoom } from "@/features/admin/ControlRoom";
import { Incidents } from "@/features/admin/Incidents";
import { Presentation } from "@/features/admin/Presentation";
import { Rounds } from "@/features/admin/Rounds";
import { Settings } from "@/features/admin/Settings";
import { Teams } from "@/features/admin/Teams";
import { Login } from "@/features/auth/Login";
import { Judging } from "@/features/judging/Judging";
import { SubmissionHistory, Workspace } from "@/features/participant/Workspace";
import { Leaderboard } from "@/features/results/Leaderboard";
import { human } from "@/lib/helpers";
import type { Confirmation, EventState, User } from "@/types";
import {
  Activity,
  CheckCheck,
  ChevronRight,
  Image as ImageIcon,
  LayoutDashboard,
  ListOrdered,
  LogOut,
  Menu,
  Radio,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Trophy,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [state, setState] = useState<EventState | null>(null);
  const [connection, setConnection] = useState(true);
  const [view, setView] = useState(
    new URLSearchParams(location.search).get("view") || "control",
  );
  const [mobile, setMobile] = useState(false);
  const [toast, setToast] = useState("");
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const notify = useCallback((s: string) => setToast(s), []);
  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);
  useEffect(() => {
    api<User>("/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!user) return;
    let active = true;
    const load = async () => {
      const began = Date.now() / 1000;
      try {
        const s = await api<EventState>("/state");
        if (active) {
          s.offset = s.server_time - (began + Date.now() / 1000) / 2;
          setState(s);
          setConnection(true);
        }
      } catch (e) {
        if (active) {
          setConnection(false);
          if (e instanceof ApiError && e.status === 401) {
            setUser(null);
            setState(null);
          }
        }
      }
    };
    void load();
    const id = setInterval(load, 2500);
    window.addEventListener("online", load);
    return () => {
      active = false;
      clearInterval(id);
      window.removeEventListener("online", load);
    };
  }, [user, refreshKey]);
  useEffect(() => {
    const title =
      view === "control" && user?.role === "participant"
        ? "Workspace"
        : view === "control" && user?.role === "judge"
          ? "Judging studio"
          : view === "workspace"
            ? "Workspace"
            : human(view);
    document.title = `${title} · Prompt Pop`;
    document.getElementById("main")?.focus();
  }, [view, user?.role]);
  useEffect(() => {
    if (!mobile) return;
    document.querySelector<HTMLButtonElement>(".sidebar nav button")?.focus();
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobile(false);
        document.querySelector<HTMLButtonElement>(".mobile-menu")?.focus();
      }
    };
    window.addEventListener("keydown", dismiss);
    return () => window.removeEventListener("keydown", dismiss);
  }, [mobile]);
  const go = (v: string) => {
    setView(v);
    setToast("");
    setMobile(false);
    history.replaceState(null, "", "?view=" + v);
  };
  if (loading)
    return (
      <div className="boot">
        <Brand />
        <p>Opening the competition…</p>
      </div>
    );
  if (!user)
    return (
      <Login
        onLogin={(u) => {
          setUser(u);
          go(
            u.role === "participant"
              ? "workspace"
              : u.role === "judge"
                ? "judging"
                : "control",
          );
        }}
      />
    );
  const participant = user.role === "participant";
  const judge = user.role === "judge";
  const nav = participant
    ? [
        ["workspace", "Your workspace", LayoutDashboard],
        ["submissions", "Your submissions", ImageIcon],
        ["leaderboard", "Leaderboard", Trophy],
      ]
    : judge
      ? [
          ["judging", "Judging studio", ImageIcon],
          ["leaderboard", "Leaderboard", Trophy],
          ["incidents", "Integrity review", ShieldCheck],
        ]
      : [
          ["control", "Control room", LayoutDashboard],
          ["rounds", "Rounds & content", ListOrdered],
          ["teams", "Teams", Users],
          ["judging", "Judging studio", ImageIcon],
          ["leaderboard", "Leaderboard", Trophy],
          ["incidents", "Integrity review", ShieldCheck],
          ["audit", "Activity log", Activity],
        ];
  const allowed =
    nav.some((n) => n[0] === view) ||
    (!participant && !judge && ["settings", "present"].includes(view));
  const currentView = allowed
    ? view
    : participant
      ? "workspace"
      : judge
        ? "judging"
        : "control";
  const common = { state: state!, notify, refresh, confirm: setConfirmation };
  return (
    <div className={"app " + (currentView === "present" ? "presenting" : "")}>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={"sidebar " + (mobile ? "open" : "")}>
        <Brand small />
        <div className="event-chip">
          <span className="event-chip-icon">
            <Radio size={19} />
          </span>
          <div>
            Prompt Pop 2K26
            <small>
              {participant
                ? "Team workspace"
                : judge
                  ? "Review workspace"
                  : "Event operations"}
            </small>
          </div>
        </div>
        <span className="nav-label">
          {participant ? "Competition" : "Manage event"}
        </span>
        <nav aria-label="Main navigation">
          {nav.map(([id, label, I]) => (
            <button
              key={id as string}
              className={"nav-item " + (currentView === id ? "active" : "")}
              aria-current={currentView === id ? "page" : undefined}
              onClick={() => go(id as string)}
            >
              <Icon icon={I as LucideIcon} />
              {label as string}
              {currentView === id && <span className="nav-active-mark" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {!participant && !judge && (
            <button
              className={"nav-item " + (view === "settings" ? "active" : "")}
              onClick={() => go("settings")}
            >
              <Settings2 size={18} />
              Event settings
            </button>
          )}
          <div className="help-panel">
            <ShieldCheck size={19} />
            <p>
              {participant
                ? "Your work belongs to your team."
                : "Fair play, by design."}
              <small>
                {participant
                  ? "Only you and the judges can see your submissions."
                  : "Server-controlled timing. Every decision recorded."}
              </small>
            </p>
          </div>
          <button
            className="account"
            onClick={async () => {
              try {
                await api("/auth/logout", { method: "POST" });
                setUser(null);
                setState(null);
              } catch (error) {
                notify((error as Error).message);
              }
            }}
            title="Sign out"
            aria-label={`Sign out ${user.team_name || user.username}`}
          >
            <span className="avatar">
              {(user.team_name || user.username).slice(0, 2).toUpperCase()}
            </span>
            <span>
              {user.team_name || user.username}
              <small>{human(user.role)}</small>
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="app-body">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Toggle navigation"
            aria-expanded={mobile}
            onClick={() => setMobile(!mobile)}
          >
            <Menu />
          </button>
          <div className="breadcrumbs">
            Competition <ChevronRight size={14} />
            <strong>{state?.title || "Prompt Pop 2K26"}</strong>
          </div>
          <div className="topbar-right">
            <span className={"connection " + (!connection ? "offline" : "")}>
              <span />
              {connection ? "Connected" : "Reconnecting"}
            </span>
            <span className="role-label">
              {participant ? "Participant" : judge ? "Judge" : "Organizer"}
            </span>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {!connection && (
            <div className="banner warning" role="alert">
              Connection interrupted. The official deadline continues.
              Reconnecting automatically; confirm any unsaved work when
              connected.
            </div>
          )}
          {!state ? (
            <div className="loading-panel">
              <RefreshCw />
              <h2>Connecting to the event</h2>
              <button className="button secondary" onClick={refresh}>
                Retry connection
              </button>
            </div>
          ) : (
            <>
              {currentView === "control" && <ControlRoom {...common} go={go} />}
              {currentView === "rounds" && <Rounds {...common} />}
              {currentView === "teams" && (
                <Teams {...common} refreshKey={refreshKey} />
              )}
              {currentView === "workspace" && (
                <Workspace {...common} user={user} connected={connection} />
              )}
              {currentView === "submissions" && (
                <SubmissionHistory {...common} />
              )}
              {currentView === "judging" && (
                <Judging {...common} refreshKey={refreshKey} />
              )}
              {currentView === "leaderboard" && (
                <Leaderboard {...common} admin={user.role === "admin"} />
              )}
              {currentView === "incidents" && <Incidents {...common} />}
              {currentView === "audit" && <AuditLog {...common} />}
              {currentView === "settings" && <Settings {...common} />}
              {currentView === "present" && <Presentation {...common} />}
            </>
          )}
        </main>
        <footer className="app-footer">
          <span>Prompt Pop 2K26</span>
          <span>Ideas take the stage.</span>
        </footer>
      </div>
      <div className={"toast " + (toast ? "visible" : "")} role="status">
        {toast && (
          <>
            <CheckCheck size={18} />
            <span>{toast}</span>
            <button
              className="icon-button"
              aria-label="Dismiss notification"
              onClick={() => setToast("")}
            >
              <X size={16} />
            </button>
          </>
        )}
      </div>
      <Confirm
        value={confirmation}
        close={() => setConfirmation(null)}
        notify={notify}
      />
    </div>
  );
}
