"use client";

import { useEffect, useState } from "react";

import { ApiError, AnalyzeJobStatus, fetchAnalyzeJob } from "@/lib/api";

const POLL_INTERVAL_MS = 3000;

function isActiveStatus(status: AnalyzeJobStatus["status"]): boolean {
  return status === "pending" || status === "processing";
}

export function useAnalyzeJob(jobId: string): {
  job: AnalyzeJobStatus | null;
  error: ApiError | Error | null;
} {
  const [job, setJob] = useState<AnalyzeJobStatus | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    const clearTimer = () => {
      if (timer !== undefined) {
        window.clearTimeout(timer);
        timer = undefined;
      }
    };

    const schedule = () => {
      clearTimer();
      timer = window.setTimeout(load, POLL_INTERVAL_MS);
    };

    async function load() {
      try {
        const next = await fetchAnalyzeJob(jobId);
        if (cancelled) {
          return;
        }
        setJob(next);
        setError(null);
        if (isActiveStatus(next.status)) {
          schedule();
        }
      } catch (caught) {
        if (cancelled) {
          return;
        }
        const nextError = caught instanceof Error ? caught : new Error("Failed to load analysis");
        setError(nextError);
        if (caught instanceof ApiError && (caught.status === 401 || caught.status === 403 || caught.status === 404)) {
          return;
        }
        schedule();
      }
    }

    void load();
    return () => {
      cancelled = true;
      clearTimer();
    };
  }, [jobId]);

  return { job, error };
}
