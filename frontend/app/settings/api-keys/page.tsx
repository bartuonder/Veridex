"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { ApiError, ApiKeyListItem, CreatedApiKey, createApiKey, deleteApiKey, listApiKeys, logout } from "@/lib/api";

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
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<CreatedApiKey | null>(null);
  const [copied, setCopied] = useState(false);
  const [deletingId, setDeletingId] = useState("");

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

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setCopied(false);
    setCreating(true);
    try {
      const next = await createApiKey(name.trim());
      setCreated(next);
      setName("");
      setKeys((current) => [
        {
          id: next.id,
          name: next.name,
          created_at: next.created_at,
          last_used_at: null,
          is_active: true,
        },
        ...current.filter((item) => item.id !== next.id),
      ]);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        router.replace("/login");
        return;
      }
      setError(caught instanceof ApiError ? caught.detail : "Failed to create API key");
    } finally {
      setCreating(false);
    }
  }

  async function onDelete(keyId: string) {
    setError("");
    setDeletingId(keyId);
    try {
      await deleteApiKey(keyId);
      setKeys((current) =>
        current.map((item) => (item.id === keyId ? { ...item, is_active: false } : item)),
      );
      if (created?.id === keyId) {
        setCreated(null);
        setCopied(false);
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        router.replace("/login");
        return;
      }
      setError(caught instanceof ApiError ? caught.detail : "Failed to delete API key");
    } finally {
      setDeletingId("");
    }
  }

  async function onCopy() {
    if (created === null) {
      return;
    }
    await navigator.clipboard.writeText(created.key);
    setCopied(true);
  }

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
      <form
        className="mt-8 space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
        onSubmit={onCreate}
      >
        <label className="block">
          <span className="text-sm font-medium text-zinc-700">Key name</span>
          <input
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
            type="text"
            name="name"
            required
            maxLength={100}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <button
          className="rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
          type="submit"
          disabled={creating}
        >
          {creating ? "Creating..." : "Yeni key oluştur"}
        </button>
      </form>
      {created ? (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <p className="text-sm font-medium text-amber-900">
            Bu anahtarı şimdi kopyala, bir daha gösterilmeyecek.
          </p>
          <p className="mt-3 break-all font-mono text-sm text-zinc-900">{created.key}</p>
          <button
            className="mt-4 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium text-zinc-900"
            type="button"
            onClick={onCopy}
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      ) : null}
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
            <li key={item.id} className="flex items-start justify-between gap-4 px-5 py-4">
              <div>
                <p className="font-medium text-zinc-900">{item.name}</p>
                <p className="mt-1 text-xs text-zinc-500">{formatTimestamp(item.created_at)}</p>
                <p className="mt-1 text-xs text-zinc-500">{item.is_active ? "Active" : "Inactive"}</p>
              </div>
              {item.is_active ? (
                <button
                  className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700 disabled:opacity-60"
                  type="button"
                  disabled={deletingId === item.id}
                  onClick={() => void onDelete(item.id)}
                >
                  {deletingId === item.id ? "Siliniyor..." : "Sil"}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
