import { api, send } from "@/api";
import { Brand } from "@/components/ui";
import { roundNames } from "@/lib/helpers";
import type { User } from "@/types";
import { ArrowRight, CircleHelp, ShieldCheck } from "lucide-react";
import { useState } from "react";
export function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login-page">
      <section className="login-story">
        <Brand />
        <div className="login-story-body">
          <span className="edition">The 2026 edition</span>
          <h1>
            A little knowledge.
            <br />A lot of imagination.
          </h1>
          <p>
            Three rounds. One creative arena.
            <br />
            Make every prompt count.
          </p>
          <div className="poster-mark" aria-hidden="true">
            <span>p</span>
            <span>p</span>
            <div className="poster-orbit" />
          </div>
        </div>
        <div className="login-rounds">
          {roundNames.map((n, i) => (
            <span key={n}>
              <b>0{i + 1}</b>
              {n}
            </span>
          ))}
        </div>
      </section>
      <section className="login-form">
        <div className="login-top">
          <span>Prompt Pop 2K26</span>
          <ShieldCheck size={19} />
        </div>
        <div className="login-form-inner">
          <div className="entry-icon">
            <ArrowRight size={27} />
          </div>
          <h2>Welcome to the arena.</h2>
          <p>
            Sign in with the account and access code
            <br className="desktop-break" /> provided by your event organizer.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              const f = new FormData(e.currentTarget);
              try {
                onLogin(
                  await api<User>(
                    "/auth/login",
                    send("POST", Object.fromEntries(f)),
                  ),
                );
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Account
              <input
                name="username"
                autoComplete="username"
                placeholder="Your team or organizer account"
                required
                maxLength={100}
              />
            </label>
            <label>
              Access code
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your access code"
                required
                maxLength={200}
              />
            </label>
            <div className="form-error" role="alert">
              {error}
            </div>
            <button className="button primary wide" disabled={busy}>
              {busy ? (
                "Signing in…"
              ) : (
                <>
                  Enter the competition <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
          <div className="login-note">
            <CircleHelp size={18} />
            <p>
              Need an account? Your organizer can register your team or reset
              your access code.
            </p>
          </div>
        </div>
        <footer>Built for ideas. Run with precision.</footer>
      </section>
    </div>
  );
}
