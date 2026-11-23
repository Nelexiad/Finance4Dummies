export interface HealthStatus {
  status: "ok";
  app: string;
  environment: string;
}

export interface ReadinessStatus {
  status: "ok" | "degraded";
  dependencies: {
    database: "ok" | "error";
    redis: "ok" | "error";
  };
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalized}`;
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed (${response.status} ${response.statusText})`);
  }

  return (await response.json()) as T;
}

export function fetchHealth(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>("/api/v1/health");
}

export function fetchReadiness(): Promise<ReadinessStatus> {
  return fetchJson<ReadinessStatus>("/api/v1/health/ready");
}
