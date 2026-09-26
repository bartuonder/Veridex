import { cookies } from "next/headers";

import { ACCESS_COOKIE } from "@/lib/auth-cookies";

const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function proxy(request: Request, path: string[]): Promise<Response> {
  const target = `${BACKEND}/${path.join("/")}${new URL(request.url).search}`;
  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  if (authorization !== null) {
    headers.set("authorization", authorization);
  } else {
    const jar = await cookies();
    const cookieToken = jar.get(ACCESS_COOKIE)?.value;
    if (cookieToken) {
      headers.set("authorization", `Bearer ${cookieToken}`);
    }
  }
  const apiKey = request.headers.get("x-api-key");
  if (apiKey !== null) {
    headers.set("x-api-key", apiKey);
  }
  const contentType = request.headers.get("content-type");
  if (contentType !== null) {
    headers.set("content-type", contentType);
  }
  const method = request.method;
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();
  const upstream = await fetch(target, { method, headers, body });
  const responseHeaders = new Headers();
  const upstreamType = upstream.headers.get("content-type");
  if (upstreamType !== null) {
    responseHeaders.set("content-type", upstreamType);
  }
  return new Response(await upstream.text(), { status: upstream.status, headers: responseHeaders });
}

export async function GET(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}

export async function POST(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}

export async function PUT(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}

export async function PATCH(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}

export async function DELETE(request: Request, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, (await context.params).path);
}
