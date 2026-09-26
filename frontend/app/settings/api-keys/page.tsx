import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { backendFetch } from "@/lib/backend";

import { CREATED_KEY_COOKIE, createApiKeyAction, deleteApiKeyAction, dismissCreatedKeyAction } from "./actions";

type ApiKeyItem = {
  id: string;
  name: string;
  created_at: string;
  is_active: boolean;
};

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toISOString().replace("T", " ").slice(0, 19);
}

export default async function ApiKeysPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const listResponse = await backendFetch("/auth/api-keys");
  if (listResponse.status === 401) {
    redirect("/login");
  }
  const keys = (listResponse.ok ? ((await listResponse.json()) as ApiKeyItem[]) : []);
  const jar = await cookies();
  const createdKey = jar.get(CREATED_KEY_COOKIE)?.value ?? "";

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
      <form className="mt-8 space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm" action={createApiKeyAction}>
        <label className="block">
          <span className="text-sm font-medium text-zinc-700">Key name</span>
          <input
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
            type="text"
            name="name"
            maxLength={100}
            required
          />
        </label>
        <button className="rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white" type="submit">
          Yeni key oluştur
        </button>
      </form>
      {createdKey ? (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <p className="text-sm font-medium text-amber-900">
            Bu anahtarı şimdi kopyala, bir daha gösterilmeyecek.
          </p>
          <input
            className="mt-3 w-full rounded-lg border border-amber-200 bg-white px-3 py-2 font-mono text-sm text-zinc-900"
            readOnly
            value={createdKey}
          />
          <form className="mt-4" action={dismissCreatedKeyAction}>
            <button
              className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium text-zinc-900"
              type="submit"
            >
              Gizle
            </button>
          </form>
        </div>
      ) : null}
      {error === "name" ? (
        <p className="mt-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">Enter a key name.</p>
      ) : null}
      {error === "create" ? (
        <p className="mt-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">Could not create the API key.</p>
      ) : null}
      {!listResponse.ok && error !== "create" && error !== "name" ? (
        <p className="mt-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">Could not load API keys.</p>
      ) : null}
      {keys.length === 0 ? (
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
                <form action={deleteApiKeyAction}>
                  <input type="hidden" name="key_id" value={item.id} />
                  <button
                    className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700"
                    type="submit"
                  >
                    Sil
                  </button>
                </form>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
