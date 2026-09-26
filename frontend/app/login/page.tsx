import Link from "next/link";

import { loginAction } from "./actions";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900">Sign in</h1>
        <p className="mt-2 text-sm text-zinc-600">Use your account email and password.</p>
        <form className="mt-8 space-y-4" action={loginAction}>
          <label className="block">
            <span className="text-sm font-medium text-zinc-700">Email</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
              type="email"
              name="email"
              autoComplete="email"
              required
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-zinc-700">Password</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
              type="password"
              name="password"
              autoComplete="current-password"
              required
            />
          </label>
          {error ? (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">Invalid email or password</p>
          ) : null}
          <button
            className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white"
            type="submit"
          >
            Sign in
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-zinc-600">
          No account?{" "}
          <Link className="font-medium text-zinc-900 underline" href="/register">
            Create one
          </Link>
        </p>
      </div>
    </main>
  );
}
