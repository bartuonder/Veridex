"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/auth-cookies";

export async function logoutAction() {
  const jar = await cookies();
  jar.set(ACCESS_COOKIE, "", { httpOnly: true, sameSite: "lax", path: "/", maxAge: 0 });
  jar.set(REFRESH_COOKIE, "", { httpOnly: true, sameSite: "lax", path: "/", maxAge: 0 });
  redirect("/login");
}
