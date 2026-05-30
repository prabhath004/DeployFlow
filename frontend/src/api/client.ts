export const TOKEN_KEY = "deployflow_token";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:8000";

export class ApiError extends Error {
  public readonly status: number;
  public readonly detail: string;

  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function handleUnauthorized(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
  // Only redirect if we're not already on /login to avoid loops.
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.assign("/login");
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, headers, ...rest } = options;
  const token = auth ? getToken() : null;

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(rest.body && !(rest.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(headers as Record<string, string> | undefined),
  };
  if (token) finalHeaders["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: finalHeaders,
    });
  } catch (e) {
    throw new ApiError(0, e instanceof Error ? e.message : "Network error");
  }

  if (res.status === 401 && auth) {
    handleUnauthorized();
    throw new ApiError(401, "Session expired — please sign in again.");
  }

  if (res.status === 204) {
    return undefined as unknown as T;
  }

  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }

  if (!res.ok) {
    const detail = extractDetail(parsed) ?? res.statusText ?? "Request failed";
    throw new ApiError(res.status, detail);
  }

  return parsed as T;
}

function extractDetail(parsed: unknown): string | null {
  if (!parsed) return null;
  if (typeof parsed === "string") return parsed;
  if (typeof parsed === "object") {
    const d = (parsed as { detail?: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length > 0) {
      const first = d[0] as { msg?: string };
      if (first && typeof first.msg === "string") return first.msg;
    }
  }
  return null;
}

/**
 * SSE-over-fetch. The native EventSource API cannot attach an
 * Authorization header, and the backend requires Bearer auth on
 * /deployments/{id}/logs/stream — so we manually parse the SSE stream
 * over a fetch with the right headers. Public surface matches
 * EventSource (`onmessage`, `close`).
 */
export interface SseHandle {
  close: () => void;
}

export function openSse(
  path: string,
  handlers: {
    onEvent: (event: string, data: string) => void;
    onError?: (err: Error) => void;
    onOpen?: () => void;
    onClose?: () => void;
  },
): SseHandle {
  const controller = new AbortController();
  const token = getToken();
  let closed = false;

  const close = () => {
    if (closed) return;
    closed = true;
    controller.abort();
    handlers.onClose?.();
  };

  (async () => {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: "GET",
        signal: controller.signal,
        headers: {
          Accept: "text/event-stream",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (res.status === 401) {
        handleUnauthorized();
        throw new ApiError(401, "Unauthorized");
      }
      if (!res.ok || !res.body) {
        throw new ApiError(res.status, `SSE failed: ${res.statusText}`);
      }

      handlers.onOpen?.();

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sepIdx: number;
        while ((sepIdx = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, sepIdx);
          buffer = buffer.slice(sepIdx + 2);
          parseAndDispatch(rawEvent, handlers.onEvent);
        }
      }

      close();
    } catch (err) {
      if ((err as { name?: string }).name === "AbortError") return;
      handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
      close();
    }
  })();

  return { close };
}

function parseAndDispatch(
  raw: string,
  onEvent: (event: string, data: string) => void,
): void {
  if (!raw.trim()) return;
  let event = "message";
  const dataLines: string[] = [];
  for (const line of raw.split("\n")) {
    if (line.startsWith(":")) continue; // SSE comment
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  if (dataLines.length === 0) return;
  onEvent(event, dataLines.join("\n"));
}
