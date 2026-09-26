import { NextResponse } from "next/server";

import { applyAuthCookies } from "@/lib/auth-cookies";
import { backendLogin, isFormPost, readAuthFields } from "@/lib/auth-form";

export async function POST(request: Request) {
  const { email, password } = await readAuthFields(request);
  const result = await backendLogin(email, password);
  if (!result.ok) {
    if (isFormPost(request)) {
      return NextResponse.redirect(new URL("/login?error=invalid", request.url), 303);
    }
    return NextResponse.json({ detail: result.detail }, { status: result.status });
  }
  if (isFormPost(request)) {
    const response = NextResponse.redirect(new URL("/dashboard", request.url), 303);
    applyAuthCookies(response, result.access_token, result.refresh_token);
    return response;
  }
  const response = NextResponse.json({
    access_token: result.access_token,
    refresh_token: result.refresh_token,
    token_type: "bearer",
  });
  applyAuthCookies(response, result.access_token, result.refresh_token);
  return response;
}
