export type StoredAnalysisJob = {
  job_id: string;
  document_name: string;
  created_at: string;
};

function browserStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function historyKey(userId: string): string {
  return `veridex_analysis_jobs:${userId}`;
}

function isStoredAnalysisJob(value: unknown): value is StoredAnalysisJob {
  if (value === null || typeof value !== "object") {
    return false;
  }
  const item = value as Partial<StoredAnalysisJob>;
  return (
    typeof item.job_id === "string" &&
    item.job_id.length > 0 &&
    typeof item.document_name === "string" &&
    typeof item.created_at === "string"
  );
}

export function loadAnalysisJobs(userId: string): StoredAnalysisJob[] {
  if (userId.length === 0) {
    return [];
  }
  const raw = browserStorage()?.getItem(historyKey(userId));
  if (raw === null || raw === undefined) {
    return [];
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(isStoredAnalysisJob);
  } catch {
    return [];
  }
}

export function addAnalysisJob(userId: string, job: StoredAnalysisJob): StoredAnalysisJob[] {
  if (userId.length === 0) {
    return [];
  }
  const next = [job, ...loadAnalysisJobs(userId).filter((item) => item.job_id !== job.job_id)];
  browserStorage()?.setItem(historyKey(userId), JSON.stringify(next));
  return next;
}
