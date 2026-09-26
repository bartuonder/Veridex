import Link from "next/link";

export default async function AnalysisPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-6 py-16">
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
      <h1 className="mt-8 text-3xl font-semibold tracking-tight text-zinc-900">Analysis</h1>
      <p className="mt-3 break-all text-zinc-600">{jobId}</p>
      <p className="mt-6 text-sm text-zinc-500">Results for this job will appear here next.</p>
      <Link className="mt-8 text-sm font-medium text-zinc-900 underline" href="/dashboard">
        Back to dashboard
      </Link>
    </main>
  );
}
