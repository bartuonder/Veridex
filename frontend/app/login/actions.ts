"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/auth-cookies";
import { backendLogin } from "@/lib/auth-form";

export async function loginAction(formData: FormData) {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");
  const result = await backendLogin(email, password);
  if (!result.ok) {
    redirect("/login?error=invalid");
  }
  const jar = await cookies();
  jar.set(ACCESS_COOKIE, result.access_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 30,
  });
  jar.set(REFRESH_COOKIE, result.refresh_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  redirect("/dashboard");
}
