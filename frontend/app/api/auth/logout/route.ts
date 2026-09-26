import { NextResponse } from "next/server";

import { clearAuthCookies } from "@/lib/auth-cookies";

export async function POST(request: Request) {
  const accept = request.headers.get("accept") ?? "";
  const response = accept.includes("application/json")
    ? new NextResponse(null, { status: 204 })
    : NextResponse.redirect(new URL("/login", request.url), 303);
  clearAuthCookies(response);
  return response;
}
