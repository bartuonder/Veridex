import { AuthGuard } from "@/components/auth-guard";

export default function ApiKeysLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
