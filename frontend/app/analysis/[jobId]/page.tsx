import { AnalysisView } from "./analysis-view";

export default async function AnalysisPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  return <AnalysisView jobId={jobId} />;
}
