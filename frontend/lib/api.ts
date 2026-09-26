const ACCESS_TOKEN_KEY = "veridex_access_token";
const REFRESH_TOKEN_KEY = "veridex_refresh_token";

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type RegisterResult = {
  id: string;
  email: string;
  plan: string;
  created_at: string;
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function browserStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

export function getAccessToken(): string | null {
  return browserStorage()?.getItem(ACCESS_TOKEN_KEY) ?? null;
}

export function getRefreshToken(): string | null {
  return browserStorage()?.getItem(REFRESH_TOKEN_KEY) ?? null;
}

export function setAccessToken(accessToken: string): void {
  browserStorage()?.setItem(ACCESS_TOKEN_KEY, accessToken);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  const storage = browserStorage();
  if (storage === null) {
    return;
  }
  storage.setItem(ACCESS_TOKEN_KEY, accessToken);
  storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  const storage = browserStorage();
  if (storage === null) {
    return;
  }
  storage.removeItem(ACCESS_TOKEN_KEY);
  storage.removeItem(REFRESH_TOKEN_KEY);
}

function extractDetail(payload: unknown, fallback: string): string {
  if (payload === null || typeof payload !== "object" || !("detail" in payload)) {
    return fallback;
  }
  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item !== null && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter((part) => part.length > 0);
    if (parts.length > 0) {
      return parts.join(" ");
    }
  }
  return fallback;
}

async function readError(response: Response): Promise<ApiError> {
  const fallback = `Request failed with status ${response.status}`;
  try {
    const payload: unknown = await response.json();
    return new ApiError(response.status, extractDetail(payload, fallback));
  } catch {
    return new ApiError(response.status, fallback);
  }
}

type ApiFetchOptions = RequestInit & {
  auth?: boolean;
};

let refreshInFlight: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight !== null) {
    return refreshInFlight;
  }
  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken === null) {
      return false;
    }
    const response = await fetch(`${getApiUrl()}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clearTokens();
      return false;
    }
    const data = (await response.json()) as { access_token: string };
    setAccessToken(data.access_token);
    return true;
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

function buildHeaders(headers: HeadersInit | undefined, body: BodyInit | null | undefined, token: string | null): Headers {
  const result = new Headers(headers);
  if (body !== undefined && body !== null && !result.has("Content-Type")) {
    result.set("Content-Type", "application/json");
  }
  if (token !== null) {
    result.set("Authorization", `Bearer ${token}`);
  }
  return result;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { auth = false, headers, ...rest } = options;
  const url = `${getApiUrl()}${path}`;

  const send = (token: string | null) =>
    fetch(url, {
      ...rest,
      headers: buildHeaders(headers, rest.body, token),
    });

  let response = await send(auth ? getAccessToken() : null);
  if (auth && response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await send(getAccessToken());
    }
  }
  if (!response.ok) {
    throw await readError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<TokenPair> {
  const tokens = await apiFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}

export async function register(email: string, password: string): Promise<RegisterResult> {
  return apiFetch<RegisterResult>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  clearTokens();
}

export type AnalyzeJobAccepted = {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  cached: boolean;
};

export async function submitAnalyze(
  documentName: string,
  documentText: string,
): Promise<AnalyzeJobAccepted> {
  return apiFetch<AnalyzeJobAccepted>("/analyze", {
    method: "POST",
    auth: true,
    body: JSON.stringify({
      document_name: documentName,
      document_text: documentText,
      contract_type: "other",
    }),
  });
}

export type JobStatus = "pending" | "processing" | "completed" | "failed";

export type ClauseFinding = {
  category: string;
  risk_level: "low" | "medium" | "high" | "critical";
  clause_text: string;
  character_start: number;
  character_end: number;
  chunk_index: number;
  confidence: number;
};

export type AnalyzeResponse = {
  analysis_id: string;
  document_name: string;
  contract_type: string;
  analyzed_at: string;
  document_characters: number;
  chunk_count: number;
  model_source: string;
  is_mock_response: boolean;
  cached: boolean;
  findings: ClauseFinding[];
  risk_summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    highest_risk_level: ClauseFinding["risk_level"] | null;
  };
  categories_without_findings: string[];
};

export type AnalyzeJobStatus = {
  job_id: string;
  status: JobStatus;
  cached: boolean;
  result: AnalyzeResponse | null;
  error: string | null;
};

export async function fetchAnalyzeJob(jobId: string): Promise<AnalyzeJobStatus> {
  return apiFetch<AnalyzeJobStatus>(`/analyze/${encodeURIComponent(jobId)}`, { auth: true });
}

export type ApiKeyListItem = {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
};

export async function listApiKeys(): Promise<ApiKeyListItem[]> {
  return apiFetch<ApiKeyListItem[]>("/auth/api-keys", { auth: true });
}
