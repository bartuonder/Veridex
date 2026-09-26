import { cookies } from "next/headers";

import { ACCESS_COOKIE } from "@/lib/auth-cookies";
import { userIdFromAccessToken } from "@/lib/jwt-sub";

import { DashboardClient } from "./dashboard-client";

export default async function DashboardPage() {
  const token = (await cookies()).get(ACCESS_COOKIE)?.value ?? "";
  const userId = token.length > 0 ? userIdFromAccessToken(token) : "";
  return <DashboardClient userId={userId} />;
}
