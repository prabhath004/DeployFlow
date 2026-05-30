import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiFetch, ApiError } from "../api/client";
import type { Project } from "../api/types";
import { Shell } from "../components/Header";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { EmptyState, ErrorMessage, Skeleton } from "../components/Skeleton";
import { relativeTime } from "../lib/time";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const list = await apiFetch<Project[]>("/projects");
      setProjects(list);
    } catch (err) {
      setProjects([]);
      if (err instanceof ApiError) setError(err.detail);
      else setError("Failed to load projects.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onCreated = (p: Project) => {
    setProjects((prev) => (prev ? [p, ...prev] : [p]));
    setShowForm(false);
  };

  return (
    <Shell>
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Your apps, deployments, and live build logs.
          </p>
        </div>
        <Button
          onClick={() => setShowForm((v) => !v)}
          variant={showForm ? "secondary" : "primary"}
        >
          {showForm ? "Cancel" : "+ New project"}
        </Button>
      </div>

      {showForm ? (
        <div className="mb-8">
          <NewProjectForm
            onCreated={onCreated}
            onCancel={() => setShowForm(false)}
          />
        </div>
      ) : null}

      {error ? (
        <div className="mb-6">
          <ErrorMessage>{error}</ErrorMessage>
        </div>
      ) : null}

      {projects === null ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          title="No projects yet"
          description="Click 'New project' to get started."
          action={
            <Button onClick={() => setShowForm(true)}>+ New project</Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </Shell>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const repoShort = truncateRepo(project.repository_url);
  return (
    <Link to={`/projects/${project.id}`} className="block">
      <Card interactive className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold text-white">
              {project.name}
            </h3>
            <p className="mt-1 truncate font-mono text-xs text-neutral-500">
              {repoShort}
            </p>
          </div>
          <span className="shrink-0 rounded-full border border-neutral-800 bg-neutral-900 px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-wider text-neutral-400">
            {project.branch}
          </span>
        </div>
        <div className="mt-6 flex items-center justify-between text-xs text-neutral-500">
          <span className="font-mono">{project.id.slice(0, 12)}…</span>
          <span>updated {relativeTime(project.updated_at)}</span>
        </div>
      </Card>
    </Link>
  );
}

function NewProjectForm({
  onCreated,
  onCancel,
}: {
  onCreated: (p: Project) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [repo, setRepo] = useState("");
  const [branch, setBranch] = useState("main");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErr(null);
    setSubmitting(true);
    try {
      const created = await apiFetch<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          repository_url: repo.trim(),
          branch: branch.trim() || "main",
        }),
      });
      onCreated(created);
    } catch (e2) {
      if (e2 instanceof ApiError) setErr(e2.detail);
      else setErr("Failed to create project.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-5">
      <h2 className="mb-4 text-sm font-semibold text-white">New project</h2>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={120}
            placeholder="my-app"
          />
          <Input
            label="Branch"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            maxLength={120}
            placeholder="main"
          />
        </div>
        <Input
          label="GitHub repository URL"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          required
          type="url"
          placeholder="https://github.com/your-org/your-repo"
        />
        {err ? <ErrorMessage>{err}</ErrorMessage> : null}
        <div className="flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button type="submit" loading={submitting} disabled={submitting}>
            Create project
          </Button>
        </div>
      </form>
    </Card>
  );
}

function truncateRepo(url: string): string {
  try {
    const u = new URL(url);
    const path = u.pathname.replace(/^\/+|\.git$/g, "");
    return `${u.host}/${path}`;
  } catch {
    return url.length > 48 ? `${url.slice(0, 48)}…` : url;
  }
}
