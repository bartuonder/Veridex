import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_COOKIE } from "@/lib/auth-cookies";

export function middleware(request: NextRequest) {
  if (request.cookies.get(ACCESS_COOKIE)?.value) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/dashboard", "/dashboard/:path*", "/settings/:path*", "/analysis/:path*"],
};
