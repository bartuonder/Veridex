import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6">
      <div className="max-w-md text-center">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-zinc-900">
          Contract clause analysis
        </h1>
        <p className="mt-3 text-zinc-600">
          Sign in to upload contracts and review high-risk clauses.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            className="rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white"
            href="/login"
          >
            Sign in
          </Link>
          <Link
            className="rounded-lg border border-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-900"
            href="/register"
          >
            Create account
          </Link>
        </div>
      </div>
    </main>
  );
}
