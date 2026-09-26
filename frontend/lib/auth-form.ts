const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function readAuthFields(request: Request): Promise<{ email: string; password: string }> {
  const contentType = request.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    const body = (await request.json()) as { email?: string; password?: string };
    return { email: String(body.email ?? ""), password: String(body.password ?? "") };
  }
  const form = await request.formData();
  return { email: String(form.get("email") ?? ""), password: String(form.get("password") ?? "") };
}

export function isFormPost(request: Request): boolean {
  const contentType = request.headers.get("content-type") ?? "";
  return !contentType.includes("application/json");
}

export async function backendLogin(email: string, password: string): Promise<
  { ok: true; access_token: string; refresh_token: string } | { ok: false; status: number; detail: string }
> {
  const response = await fetch(`${BACKEND}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const payload = (await response.json().catch(() => ({ detail: "Login failed" }))) as {
    access_token?: string;
    refresh_token?: string;
    detail?: unknown;
  };
  if (!response.ok || !payload.access_token || !payload.refresh_token) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Invalid email or password";
    return { ok: false, status: response.status, detail };
  }
  return { ok: true, access_token: payload.access_token, refresh_token: payload.refresh_token };
}

export async function backendRegister(email: string, password: string): Promise<{ ok: true } | { ok: false; status: number; detail: string }> {
  const response = await fetch(`${BACKEND}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (response.ok || response.status === 409) {
    return { ok: true };
  }
  const payload = (await response.json().catch(() => ({ detail: "Registration failed" }))) as { detail?: unknown };
  const detail = typeof payload.detail === "string" ? payload.detail : "Registration failed";
  return { ok: false, status: response.status, detail };
}
