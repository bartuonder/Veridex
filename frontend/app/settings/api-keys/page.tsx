"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, ApiKeyListItem, listApiKeys, logout } from "@/lib/api";

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toISOString().replace("T", " ").slice(0, 19);
}

export default function ApiKeysPage() {
  const router = useRouter();
  const [keys, setKeys] = useState<ApiKeyListItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const items = await listApiKeys();
        if (!cancelled) {
          setKeys(items);
          setError("");
        }
      } catch (caught) {
        if (cancelled) {
          return;
        }
        if (caught instanceof ApiError && caught.status === 401) {
          logout();
          router.replace("/login");
          return;
        }
        setError(caught instanceof ApiError ? caught.detail : "Failed to load API keys");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-6 py-16">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
        <Link className="text-sm font-medium text-zinc-900 underline" href="/dashboard">
          Back to dashboard
        </Link>
      </div>
      <h1 className="mt-8 text-3xl font-semibold tracking-tight text-zinc-900">API keys</h1>
      <p className="mt-3 text-zinc-600">Keys are shown by name and date. The raw secret is never listed.</p>
      {error ? (
        <p className="mt-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      ) : null}
      {loading ? (
        <p className="mt-6 text-sm text-zinc-500">Loading...</p>
      ) : keys.length === 0 ? (
        <p className="mt-6 text-sm text-zinc-500">No API keys yet.</p>
      ) : (
        <ul className="mt-8 divide-y divide-zinc-200 overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm">
          {keys.map((item) => (
            <li key={item.id} className="px-5 py-4">
              <p className="font-medium text-zinc-900">{item.name}</p>
              <p className="mt-1 text-xs text-zinc-500">{formatTimestamp(item.created_at)}</p>
              <p className="mt-1 text-xs text-zinc-500">{item.is_active ? "Active" : "Inactive"}</p>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
