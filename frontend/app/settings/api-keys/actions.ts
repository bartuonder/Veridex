"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { CREATED_KEY_COOKIE } from "@/lib/auth-cookies";
import { backendFetch } from "@/lib/backend";

export async function createApiKeyAction(formData: FormData) {
  const name = String(formData.get("name") ?? "").trim();
  if (name.length === 0) {
    redirect("/settings/api-keys?error=name");
  }
  const response = await backendFetch("/auth/api-keys", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  if (response.status === 401) {
    redirect("/login");
  }
  if (!response.ok) {
    redirect("/settings/api-keys?error=create");
  }
  const created = (await response.json()) as { key?: string };
  const jar = await cookies();
  if (typeof created.key === "string" && created.key.length > 0) {
    jar.set(CREATED_KEY_COOKIE, created.key, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 300,
    });
  }
  redirect("/settings/api-keys");
}

export async function deleteApiKeyAction(formData: FormData) {
  const keyId = String(formData.get("key_id") ?? "");
  if (keyId.length === 0) {
    redirect("/settings/api-keys");
  }
  const response = await backendFetch(`/auth/api-keys/${encodeURIComponent(keyId)}`, {
    method: "DELETE",
  });
  if (response.status === 401) {
    redirect("/login");
  }
  redirect("/settings/api-keys");
}

export async function dismissCreatedKeyAction() {
  const jar = await cookies();
  jar.set(CREATED_KEY_COOKIE, "", { httpOnly: true, sameSite: "lax", path: "/", maxAge: 0 });
  redirect("/settings/api-keys");
}
