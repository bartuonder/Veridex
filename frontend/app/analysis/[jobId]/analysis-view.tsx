"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { ApiError, logout } from "@/lib/api";
import { useAnalyzeJob } from "@/lib/use-analyze-job";

export function AnalysisView({ jobId }: { jobId: string }) {
  const router = useRouter();
  const { job, error } = useAnalyzeJob(jobId);

  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) {
      logout();
      router.replace("/login");
    }
  }, [error, router]);

  const active = job !== null && (job.status === "pending" || job.status === "processing");

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-6 py-16">
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
      <h1 className="mt-8 text-3xl font-semibold tracking-tight text-zinc-900">Analysis</h1>
      <p className="mt-3 break-all font-mono text-xs text-zinc-500">{jobId}</p>
      {error !== null && !(error instanceof ApiError && error.status === 401) ? (
        <p className="mt-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error instanceof ApiError ? error.detail : error.message}
        </p>
      ) : null}
      {active ? (
        <p className="mt-6 text-sm text-zinc-600">Analiz ediliyor...</p>
      ) : null}
      {job?.status === "failed" ? (
        <p className="mt-6 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {job.error ?? "Analysis failed"}
        </p>
      ) : null}
      {job?.status === "completed" ? (
        <p className="mt-6 text-sm text-zinc-600">Analysis complete.</p>
      ) : null}
      {job === null && error === null ? (
        <p className="mt-6 text-sm text-zinc-600">Analiz ediliyor...</p>
      ) : null}
      <Link className="mt-8 text-sm font-medium text-zinc-900 underline" href="/dashboard">
        Back to dashboard
      </Link>
    </main>
  );
}
