export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const csrf =
    typeof document !== "undefined"
      ? document.cookie
          .split("; ")
          .find((v) => v.startsWith("cc_csrf="))
          ?.split("=")
          .slice(1)
          .join("=")
      : "";
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {}),
      ...options.headers,
    },
  });
  const data = await response
    .json()
    .catch(() => ({ detail: "The server returned an invalid response" }));
  if (!response.ok) {
    if (
      response.status === 401 &&
      path !== "/auth/login" &&
      typeof window !== "undefined"
    )
      window.location.assign("/login");
    throw new ApiError(
      response.status,
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((e: { msg: string }) => e.msg).join("; ")
          : "Request failed",
    );
  }
  return data;
}
export const post = <T = unknown>(path: string, body: unknown = {}) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export type Project = {
  id: string;
  name: string;
  market: string;
  niche: string;
  status: string;
  created_at: string;
  selected_domain: string | null;
  approved_by: string | null;
  approved_at: string | null;
  deleted_at: string | null;
};
export type Candidate = {
  id: string;
  domain: string;
  source: string;
  acquisition_url: string | null;
  acquisition_price: number | null;
  currency: string | null;
  scamadviser_score: number | null;
  history_status: string;
  backlink_status: string;
  safety_status: string;
  niche_fit_score: number | null;
  domain_score: number;
  final_status: string;
  warnings: string[];
  rejection_reasons: string[];
  historical_categories: string[];
  research_timestamp: string;
};
export type Run = {
  id: string;
  state: string;
  provider: string;
  is_demo: boolean;
  created_at: string;
  failure: string | null;
  candidates: Candidate[];
  rule_version: string;
};
export type Approval = {
  id: string;
  project_id: string;
  run_id: string;
  state: string;
  created_at: string;
  decided_at: string | null;
  decided_by: string | null;
};
export type Event = {
  id: string;
  project_id: string | null;
  actor_id: string;
  actor_type: string;
  action: string;
  created_at: string;
  outcome: string;
  details: Record<string, unknown>;
  request_id: string;
};
export type Settings = {
  storage_backend: string;
  fixtures_enabled: boolean;
  live_providers_configured: boolean;
  rule_version: string;
  scamadviser_minimum: number;
  candidate_limit: number;
  approval_policy: string;
  purchasing_enabled: boolean;
  cookie_secure: boolean;
};
export const date = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
