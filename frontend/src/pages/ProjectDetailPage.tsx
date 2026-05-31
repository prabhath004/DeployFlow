import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, ApiError } from "../api/client";
import type { Deployment, Project } from "../api/types";
import { isTerminal } from "../api/types";
import { Shell } from "../components/Header";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState, ErrorMessage, Skeleton } from "../components/Skeleton";
import { relativeTime } from "../lib/time";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [deployments, setDeployments] = useState<Deployment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deploying, setDeploying] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setError(null);
    try {
      const [p, d] = await Promise.all([
        apiFetch<Project>(`/projects/${id}`),
        apiFetch<Deployment[]>(`/projects/${id}/deployments`),
      ]);
      setProject(p);
      setDeployments(d);
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Failed to load project.");
      // Make sure the skeleton state resolves to an empty list on first-load failure.
      setDeployments((prev) => prev ?? []);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Light polling: if any deployment is non-terminal, refresh list every 3s.
  useEffect(() => {
    if (!deployments || deployments.length === 0) return;
    const anyActive = deployments.some((d) => !isTerminal(d.status));
    if (!anyActive) return;
    const handle = window.setInterval(() => {
      void load();
    }, 3000);
    return () => window.clearInterval(handle);
  }, [deployments, load]);

  const deploy = async () => {
    if (!id) return;
    setDeploying(true);
    setError(null);
    try {
      const created = await apiFetch<Deployment>(
        `/projects/${id}/deployments`,
        { method: "POST", body: JSON.stringify({}) },
      );
      setDeployments((prev) => (prev ? [created, ...prev] : [created]));
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Failed to trigger deployment.");
    } finally {
      setDeploying(false);
    }
  };

  const retry = async (depId: string) => {
    setActionId(depId);
    setError(null);
    try {
      const updated = await apiFetch<Deployment>(
        `/deployments/${depId}/retry`,
        { method: "POST" },
      );
      setDeployments((prev) =>
        prev ? prev.map((d) => (d.id === depId ? updated : d)) : prev,
      );
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Retry failed.");
    } finally {
      setActionId(null);
    }
  };

  const cancel = async (depId: string) => {
    setActionId(depId);
    setError(null);
    try {
      const updated = await apiFetch<Deployment>(
        `/deployments/${depId}/cancel`,
        { method: "POST" },
      );
      setDeployments((prev) =>
        prev ? prev.map((d) => (d.id === depId ? updated : d)) : prev,
      );
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Cancel failed.");
    } finally {
      setActionId(null);
    }
  };

  const deleteDeployment = async (depId: string) => {
    const confirmed = window.confirm("Delete this deployment and its logs?");
    if (!confirmed) return;
    setActionId(depId);
    setError(null);
    try {
      await apiFetch<void>(`/deployments/${depId}`, { method: "DELETE" });
      setDeployments((prev) =>
        prev ? prev.filter((d) => d.id !== depId) : prev,
      );
    } catch (err) {
      if (err instanceof ApiError) setError(err.detail);
      else setError("Delete failed.");
    } finally {
      setActionId(null);
    }
  };

  return (
    <Shell>
      {!project ? (
        <div className="space-y-4">
          <Skeleton className="h-10 w-1/3" />
          <Skeleton className="h-5 w-1/2" />
        </div>
      ) : (
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <Link
                to="/projects"
                className="font-mono text-xs text-neutral-500 hover:text-white"
              >
                ← projects
              </Link>
            </div>
            <h1 className="mt-2 truncate text-2xl font-semibold tracking-tight">
              {project.name}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-neutral-500">
              <a
                href={project.repository_url}
                target="_blank"
                rel="noreferrer"
                className="font-mono text-xs text-neutral-400 transition-colors hover:text-white"
              >
                {project.repository_url}
              </a>
              <span className="text-neutral-700">·</span>
              <span className="rounded-full border border-neutral-800 bg-neutral-900 px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider text-neutral-400">
                {project.branch}
              </span>
            </div>
          </div>
          <Button onClick={deploy} loading={deploying} disabled={deploying}>
            Deploy
          </Button>
        </div>
      )}

      {error ? (
        <div className="mb-6">
          <ErrorMessage>{error}</ErrorMessage>
        </div>
      ) : null}

      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">
          Deployments
        </h2>
        {deployments === null ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : deployments.length === 0 ? (
          <EmptyState
            title="No deployments yet"
            description="Click 'Deploy' to trigger your first build."
          />
        ) : (
          <Card className="divide-y divide-neutral-900">
            {deployments.map((d) => (
              <DeploymentRow
                key={d.id}
                dep={d}
                onRetry={() => retry(d.id)}
                onCancel={() => cancel(d.id)}
                onDelete={() => deleteDeployment(d.id)}
                busy={actionId === d.id}
              />
            ))}
          </Card>
        )}
      </section>
    </Shell>
  );
}

function DeploymentRow({
  dep,
  onRetry,
  onCancel,
  onDelete,
  busy,
}: {
  dep: Deployment;
  onRetry: () => void;
  onCancel: () => void;
  onDelete: () => void;
  busy: boolean;
}) {
  const shortId = dep.id.length > 12 ? dep.id.slice(-12) : dep.id;
  const canRetry = dep.status === "FAILED";
  const canCancel = !isTerminal(dep.status);
  const canDelete = isTerminal(dep.status);

  return (
    <div className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <Link
        to={`/deployments/${dep.id}`}
        className="flex min-w-0 flex-1 items-center gap-4"
      >
        <span className="font-mono text-xs text-neutral-400">{shortId}</span>
        <StatusBadge status={dep.status} />
        <span className="hidden truncate font-mono text-xs text-neutral-500 sm:inline">
          {dep.branch}
        </span>
        <span className="ml-auto hidden text-xs text-neutral-500 sm:inline">
          {relativeTime(dep.created_at)}
        </span>
      </Link>
      <div className="flex shrink-0 items-center gap-2">
        {canRetry ? (
          <Button
            size="sm"
            variant="secondary"
            onClick={(e) => {
              e.preventDefault();
              onRetry();
            }}
            disabled={busy}
            loading={busy}
          >
            Retry
          </Button>
        ) : null}
        {canCancel ? (
          <Button
            size="sm"
            variant="danger"
            onClick={(e) => {
              e.preventDefault();
              onCancel();
            }}
            disabled={busy}
            loading={busy}
          >
            Cancel
          </Button>
        ) : null}
        {canDelete ? (
          <Button
            size="sm"
            variant="danger"
            onClick={(e) => {
              e.preventDefault();
              onDelete();
            }}
            disabled={busy}
            loading={busy}
          >
            Delete
          </Button>
        ) : null}
      </div>
    </div>
  );
}
