import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACCESS_COOKIE } from "@/lib/auth-cookies";

export async function GET() {
  const jar = await cookies();
  return NextResponse.json({ ok: Boolean(jar.get(ACCESS_COOKIE)?.value) });
}
