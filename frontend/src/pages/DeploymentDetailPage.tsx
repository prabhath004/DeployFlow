import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiFetch, ApiError, openSse } from "../api/client";
import type { Deployment, LogEntry } from "../api/types";
import { isTerminal } from "../api/types";
import { Shell } from "../components/Header";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { StatusBadge } from "../components/StatusBadge";
import { ErrorMessage, Skeleton } from "../components/Skeleton";
import { formatTimestamp, logTimestamp, relativeTime } from "../lib/time";

export default function DeploymentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dep, setDep] = useState<Deployment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const d = await apiFetch<Deployment>(`/deployments/${id}`);
      setDep(d);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Failed to load deployment.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll /status every 1s until terminal. Refresh full deployment when status changes.
  useEffect(() => {
    if (!id || !dep) return;
    if (isTerminal(dep.status)) return;
    let cancelled = false;
    const handle = window.setInterval(async () => {
      try {
        const r = await apiFetch<{ deployment_id: string; status: string }>(
          `/deployments/${id}/status`,
        );
        if (cancelled) return;
        if (r.status !== dep.status) {
          // pull the full row so all fields update
          void load();
        }
      } catch {
        /* swallow polling errors */
      }
    }, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, [id, dep, load]);

  const retry = async () => {
    if (!id) return;
    setActionBusy(true);
    setError(null);
    try {
      const updated = await apiFetch<Deployment>(
        `/deployments/${id}/retry`,
        { method: "POST" },
      );
      setDep(updated);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Retry failed.");
    } finally {
      setActionBusy(false);
    }
  };

  const cancel = async () => {
    if (!id) return;
    setActionBusy(true);
    setError(null);
    try {
      const updated = await apiFetch<Deployment>(
        `/deployments/${id}/cancel`,
        { method: "POST" },
      );
      setDep(updated);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Cancel failed.");
    } finally {
      setActionBusy(false);
    }
  };

  const deleteDeployment = async () => {
    if (!id || !dep) return;
    const confirmed = window.confirm("Delete this deployment and its logs?");
    if (!confirmed) return;
    setActionBusy(true);
    setError(null);
    try {
      await apiFetch<void>(`/deployments/${id}`, { method: "DELETE" });
      navigate(`/projects/${dep.project_id}`, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Delete failed.");
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <Shell>
      <div className="mb-6">
        <Link
          to={dep ? `/projects/${dep.project_id}` : "/projects"}
          className="font-mono text-xs text-neutral-500 hover:text-white"
        >
          ← back
        </Link>
      </div>

      {error ? (
        <div className="mb-6">
          <ErrorMessage>{error}</ErrorMessage>
        </div>
      ) : null}

      {!dep ? (
        <div className="space-y-4">
          <Skeleton className="h-12 w-2/3" />
          <Skeleton className="h-40" />
        </div>
      ) : (
        <>
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-3">
                <StatusBadge status={dep.status} size="md" />
                <span className="font-mono text-xs text-neutral-500">
                  attempt #{dep.attempt}
                </span>
              </div>
              <h1 className="mt-3 break-all font-mono text-lg font-semibold text-white">
                {dep.id}
              </h1>
              <p className="mt-1 text-sm text-neutral-500">
                triggered {relativeTime(dep.created_at)}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {dep.status === "FAILED" ? (
                <Button
                  variant="secondary"
                  onClick={retry}
                  disabled={actionBusy}
                  loading={actionBusy}
                >
                  Retry
                </Button>
              ) : null}
              {!isTerminal(dep.status) ? (
                <Button
                  variant="danger"
                  onClick={cancel}
                  disabled={actionBusy}
                  loading={actionBusy}
                >
                  Cancel
                </Button>
              ) : null}
              {isTerminal(dep.status) ? (
                <Button
                  variant="danger"
                  onClick={deleteDeployment}
                  disabled={actionBusy}
                  loading={actionBusy}
                >
                  Delete
                </Button>
              ) : null}
            </div>
          </div>

          <DeploymentFields dep={dep} />

          <section className="mt-8">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
                Build logs
              </h2>
            </div>
            <LogViewer deploymentId={dep.id} terminal={isTerminal(dep.status)} />
          </section>
        </>
      )}
    </Shell>
  );
}

function DeploymentFields({ dep }: { dep: Deployment }) {
  const rows: Array<[string, string]> = [
    ["Project", dep.project_id],
    ["Branch", dep.branch],
    ["Commit", dep.commit_sha ?? "—"],
    ["Image", dep.image_uri ?? "—"],
    ["URL", dep.deployment_url ?? "—"],
    ["Started", formatTimestamp(dep.started_at)],
    ["Finished", formatTimestamp(dep.finished_at)],
    ["Created", formatTimestamp(dep.created_at)],
    ["Updated", formatTimestamp(dep.updated_at)],
  ];
  return (
    <Card className="p-5">
      <dl className="grid grid-cols-1 gap-y-3 sm:grid-cols-2 sm:gap-x-8">
        {rows.map(([label, value]) => (
          <div key={label} className="flex flex-col">
            <dt className="text-[0.65rem] font-semibold uppercase tracking-wider text-neutral-500">
              {label}
            </dt>
            <dd className="mt-0.5 break-all font-mono text-xs text-neutral-300">
              {label === "URL" && value !== "—" ? (
                <a
                  href={value}
                  target="_blank"
                  rel="noreferrer"
                  className="text-emerald-300 hover:text-emerald-200"
                >
                  {value}
                </a>
              ) : (
                value
              )}
            </dd>
          </div>
        ))}
        {dep.error_message ? (
          <div className="sm:col-span-2">
            <dt className="text-[0.65rem] font-semibold uppercase tracking-wider text-red-400">
              Error
            </dt>
            <dd className="mt-1 whitespace-pre-wrap font-mono text-xs text-red-300">
              {dep.error_message}
            </dd>
          </div>
        ) : null}
      </dl>
    </Card>
  );
}

interface ViewerLog {
  key: string;
  level: string;
  source: string;
  message: string;
  ts: string | undefined;
}

function LogViewer({
  deploymentId,
  terminal,
}: {
  deploymentId: string;
  terminal: boolean;
}) {
  const [logs, setLogs] = useState<ViewerLog[]>([]);
  const [streamState, setStreamState] = useState<
    "connecting" | "open" | "closed" | "error"
  >("connecting");
  const [streamError, setStreamError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const stickToBottomRef = useRef(true);
  const seqRef = useRef(0);

  // Track whether the user has scrolled away from the bottom.
  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distance < 24;
  };

  // Auto-scroll after each render if user is "stuck" to bottom.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (stickToBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [logs]);

  // Load historical logs, then open SSE.
  useEffect(() => {
    let cancelled = false;
    setLogs([]);
    setStreamState("connecting");
    setStreamError(null);

    (async () => {
      try {
        const historical = await apiFetch<LogEntry[]>(
          `/deployments/${deploymentId}/logs`,
        );
        if (cancelled) return;
        setLogs(
          historical.map((l) => ({
            key: `h-${l.id ?? ++seqRef.current}`,
            level: l.level,
            source: l.source,
            message: l.message,
            ts: l.created_at,
          })),
        );
      } catch {
        /* fall through; SSE may still produce logs */
      }
    })();

    // Terminal deployments may still publish historical logs, but the
    // stream may close immediately. We open SSE anyway — it gracefully
    // ends if there's nothing to send.
    const handle = openSse(`/deployments/${deploymentId}/logs/stream`, {
      onOpen: () => {
        if (!cancelled) setStreamState("open");
      },
      onEvent: (event, data) => {
        if (event !== "log" || cancelled) return;
        try {
          const parsed = JSON.parse(data) as LogEntry;
          setLogs((prev) => [
            ...prev,
            {
              key: `s-${++seqRef.current}`,
              level: parsed.level ?? "INFO",
              source: parsed.source ?? "build",
              message: parsed.message ?? "",
              ts: parsed.ts ?? parsed.created_at,
            },
          ]);
        } catch {
          /* skip malformed lines */
        }
      },
      onError: (err) => {
        if (cancelled) return;
        setStreamState("error");
        setStreamError(err.message);
      },
      onClose: () => {
        if (cancelled) return;
        setStreamState((s) => (s === "error" ? s : "closed"));
      },
    });

    return () => {
      cancelled = true;
      handle.close();
    };
  }, [deploymentId]);

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex items-center justify-between border-b border-neutral-900 px-4 py-2 text-xs">
        <div className="flex items-center gap-2 font-mono text-neutral-500">
          <StreamIndicator state={streamState} terminal={terminal} />
          <span>{logs.length} lines</span>
        </div>
        {streamState === "error" && streamError ? (
          <span className="font-mono text-[0.65rem] text-red-400">
            stream error: {streamError}
          </span>
        ) : null}
      </div>
      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="scroll-thin h-[480px] overflow-y-auto bg-black px-4 py-3 font-mono text-xs leading-relaxed"
      >
        {logs.length === 0 ? (
          <p className="text-neutral-600">
            {terminal
              ? "no logs were recorded for this deployment."
              : "waiting for log output…"}
          </p>
        ) : (
          logs.map((l) => <LogLine key={l.key} log={l} />)
        )}
      </div>
    </Card>
  );
}

function LogLine({ log }: { log: ViewerLog }) {
  const level = (log.level || "INFO").toUpperCase();
  const levelColor =
    level === "ERROR"
      ? "text-red-400"
      : level === "WARN" || level === "WARNING"
        ? "text-amber-400"
        : "text-neutral-300";
  return (
    <div className="flex gap-3 py-0.5">
      <span className="shrink-0 text-neutral-600">{logTimestamp(log.ts)}</span>
      <span
        className={`w-12 shrink-0 text-[0.65rem] font-semibold uppercase tracking-wider ${levelColor}`}
      >
        {level}
      </span>
      <span className={`whitespace-pre-wrap break-words ${levelColor}`}>
        {log.message}
      </span>
    </div>
  );
}

function StreamIndicator({
  state,
  terminal,
}: {
  state: "connecting" | "open" | "closed" | "error";
  terminal: boolean;
}) {
  if (terminal && (state === "closed" || state === "open")) {
    return (
      <span className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-neutral-500" />
        terminal
      </span>
    );
  }
  if (state === "open") {
    return (
      <span className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-emerald-400" />
        live
      </span>
    );
  }
  if (state === "connecting") {
    return (
      <span className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-amber-400" />
        connecting
      </span>
    );
  }
  if (state === "error") {
    return (
      <span className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
        disconnected
      </span>
    );
  }
  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-1.5 rounded-full bg-neutral-500" />
      idle
    </span>
  );
}
