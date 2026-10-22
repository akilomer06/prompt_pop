import type { Confirmation, EventState, Task } from "@/types";
import { ClipboardList, Flag, X, type LucideIcon } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";
export function Brand({ small = false }: { small?: boolean }) {
  return (
    <div className={"brand " + (small ? "small" : "")}>
      <span className="brand-symbol" aria-hidden="true">
        p<span />
      </span>
      <div>
        prompt<span className="brand-pop">pop</span>
        <small>2K26 / THE CREATIVE COMPETITION</small>
      </div>
    </div>
  );
}
export function Icon({
  icon: Icon,
  ...props
}: {
  icon: LucideIcon;
  size?: number;
  className?: string;
}) {
  return <Icon size={18} strokeWidth={1.7} aria-hidden="true" {...props} />;
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function Empty({
  icon: Icon = ClipboardList,
  title,
  children,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon size={27} strokeWidth={1.5} />
      </div>
      <h3>{title}</h3>
      <div className="empty-copy">{children}</div>
      {action}
    </div>
  );
}
export function Timer({
  task,
  state,
  large = false,
}: {
  task?: Task;
  state: EventState;
  large?: boolean;
}) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);
  let s =
    task?.status === "ended"
      ? 0
      : task?.status === "paused"
        ? task.remaining || 0
        : task?.deadline
          ? task.deadline - (now / 1000 + state.offset)
          : task?.duration || 0;
  const grace = s <= 0 && task?.status === "running" && (task.grace || 0) > 0;
  if (grace) s += task!.grace;
  s = Math.max(0, Math.ceil(s));
  return (
    <div
      className={
        "timer " +
        (large ? "large " : "") +
        (s < 60 && task?.status === "running" ? "urgent" : "")
      }
      role="timer"
      aria-label={`${Math.floor(s / 60)} minutes ${s % 60} seconds ${grace ? "submission grace" : ""}`}
    >
      <span>
        {String(Math.floor(s / 60)).padStart(2, "0")}
        <i>:</i>
        {String(s % 60).padStart(2, "0")}
      </span>
      <small>
        {task?.status === "paused"
          ? "Timer paused"
          : task?.status === "ended"
            ? "Task closed"
            : grace
              ? "Submission grace"
              : task?.status === "pending" || !task
                ? "Ready when you are"
                : "Official time remaining"}
      </small>
    </div>
  );
}

export function Confirm({
  value,
  close,
  notify,
}: {
  value: Confirmation | null;
  close: () => void;
  notify: (v: string) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (value) ref.current?.showModal();
    else ref.current?.close();
  }, [value]);
  return (
    <dialog
      ref={ref}
      onKeyDown={(e) => {
        if (e.key !== "Tab") return;
        const items = ref.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),a[href],input:not(:disabled),textarea:not(:disabled),select:not(:disabled),[tabindex="0"]',
        );
        if (!items?.length) {
          e.preventDefault();
          return;
        }
        const first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }}
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else close();
      }}
      aria-labelledby="confirm-title"
    >
      <div className="dialog-heading">
        <span className="dialog-icon">
          <Flag />
        </span>
        <button
          className="icon-button"
          aria-label="Close confirmation"
          onClick={close}
          disabled={busy}
        >
          <X />
        </button>
      </div>
      <h2 id="confirm-title">{value?.title}</h2>
      <p>{value?.description}</p>
      <div className="dialog-actions">
        <button className="button secondary" disabled={busy} onClick={close}>
          Cancel
        </button>
        <button
          className={"button " + (value?.danger ? "danger" : "primary")}
          disabled={busy}
          onClick={async () => {
            if (!value) return;
            setBusy(true);
            try {
              await value.action();
              close();
            } catch (e) {
              notify((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Working…" : value?.label}
        </button>
      </div>
    </dialog>
  );
}

export function Heading({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  );
}
export function ResourceError({
  error,
  retry,
}: {
  error: string;
  retry: () => void;
}) {
  return error ? (
    <div className="banner warning" role="alert">
      {error}
      <button className="text-button" onClick={retry}>
        Retry
      </button>
    </div>
  ) : null;
}
