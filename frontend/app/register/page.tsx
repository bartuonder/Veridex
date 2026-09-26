"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError, registerAndLogin } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      await registerAndLogin(email, password);
      router.push("/dashboard");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Registration failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900">Create account</h1>
        <p className="mt-2 text-sm text-zinc-600">Password must be at least 8 characters.</p>
        <form className="mt-8 space-y-4" method="post" action="" onSubmit={onSubmit}>
          <label className="block">
            <span className="text-sm font-medium text-zinc-700">Email</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
              type="email"
              name="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-zinc-700">Password</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
              type="password"
              name="password"
              autoComplete="new-password"
              minLength={8}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          ) : null}
          <button
            className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
            type="submit"
            disabled={pending}
          >
            {pending ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-zinc-600">
          Already have an account?{" "}
          <Link className="font-medium text-zinc-900 underline" href="/login">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
