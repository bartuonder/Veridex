"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getAccessToken, logout } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (getAccessToken() === null) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  function onLogout() {
    logout();
    router.replace("/login");
  }

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <p className="text-sm text-zinc-500">Loading...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-6 py-16">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
        <button
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700"
          type="button"
          onClick={onLogout}
        >
          Sign out
        </button>
      </div>
      <h1 className="mt-8 text-3xl font-semibold tracking-tight text-zinc-900">Dashboard</h1>
      <p className="mt-3 text-zinc-600">You are signed in. Contract analysis will live here next.</p>
    </main>
  );
}
