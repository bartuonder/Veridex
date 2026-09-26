"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { addAnalysisJob, loadAnalysisJobs, StoredAnalysisJob } from "@/lib/analysis-history";
import { ApiError, logout, submitAnalyze } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [documentName, setDocumentName] = useState("pasted-contract.txt");
  const [documentText, setDocumentText] = useState("");
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState("");
  const [pending, setPending] = useState(false);
  const [jobs, setJobs] = useState<StoredAnalysisJob[]>([]);

  useEffect(() => {
    setJobs(loadAnalysisJobs());
  }, []);

  function onLogout() {
    logout();
    router.replace("/login");
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setJobId("");
    setPending(true);
    try {
      const accepted = await submitAnalyze(documentName.trim(), documentText);
      setJobId(accepted.job_id);
      setJobs(
        addAnalysisJob({
          job_id: accepted.job_id,
          document_name: documentName.trim(),
          created_at: new Date().toISOString(),
        }),
      );
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        router.replace("/login");
        return;
      }
      setError(caught instanceof ApiError ? caught.detail : "Analyze request failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-6 py-16">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-500">Veridex</p>
        <div className="flex items-center gap-3">
          <Link className="text-sm font-medium text-zinc-900 underline" href="/settings/api-keys">
            API keys
          </Link>
          <button
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700"
            type="button"
            onClick={onLogout}
          >
            Sign out
          </button>
        </div>
      </div>
      <h1 className="mt-8 text-3xl font-semibold tracking-tight text-zinc-900">Dashboard</h1>
      <p className="mt-3 text-zinc-600">Paste a contract and send it for analysis.</p>
      <form
        className="mt-8 space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm"
        method="post"
        action=""
        onSubmit={onSubmit}
      >
        <label className="block">
          <span className="text-sm font-medium text-zinc-700">Document name</span>
          <input
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
            type="text"
            name="document_name"
            required
            maxLength={255}
            value={documentName}
            onChange={(event) => setDocumentName(event.target.value)}
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-zinc-700">Contract text</span>
          <textarea
            className="mt-1 min-h-48 w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-sm text-zinc-900 outline-none ring-zinc-900 focus:ring-2"
            name="document_text"
            required
            value={documentText}
            onChange={(event) => setDocumentText(event.target.value)}
          />
        </label>
        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        ) : null}
        {jobId ? (
          <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            Job queued: {jobId}
          </p>
        ) : null}
        <button
          className="rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
          type="submit"
          disabled={pending}
        >
          {pending ? "Sending..." : "Analyze contract"}
        </button>
      </form>
      <section className="mt-10">
        <h2 className="text-lg font-semibold tracking-tight text-zinc-900">Geçmiş Analizler</h2>
        {jobs.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No analyses yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-zinc-200 overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm">
            {jobs.map((job) => (
              <li key={job.job_id}>
                <Link
                  className="block px-5 py-4 transition-colors hover:bg-zinc-50"
                  href={`/analysis/${job.job_id}`}
                >
                  <p className="font-medium text-zinc-900">{job.document_name}</p>
                  <p className="mt-1 break-all font-mono text-xs text-zinc-500">{job.job_id}</p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
