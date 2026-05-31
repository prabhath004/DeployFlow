export type DeploymentStatus =
  | "PENDING"
  | "QUEUED"
  | "RUNNING"
  | "BUILDING"
  | "PUSHING_IMAGE"
  | "DEPLOYING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED"
  | "RETRYING";

export const TERMINAL_STATUSES: DeploymentStatus[] = [
  "SUCCEEDED",
  "FAILED",
  "CANCELLED",
];

export function isTerminal(s: string): boolean {
  return TERMINAL_STATUSES.includes(s as DeploymentStatus);
}

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_at: string;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  repository_url: string;
  branch: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Deployment {
  id: string;
  project_id: string;
  user_id: string;
  status: DeploymentStatus | string;
  branch: string;
  commit_sha: string | null;
  image_uri: string | null;
  deployment_url: string | null;
  error_message: string | null;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LogEntry {
  id?: string;
  deployment_id?: string;
  level: string;
  source: string;
  message: string;
  // historical logs use `created_at`; live SSE logs publish `ts`.
  created_at?: string;
  ts?: string;
}

export interface ApiErrorDetail {
  status: number;
  detail: string;
}
