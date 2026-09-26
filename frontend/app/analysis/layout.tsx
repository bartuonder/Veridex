import { AuthGuard } from "@/components/auth-guard";

export default function AnalysisLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
