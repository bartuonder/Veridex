"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { getAccessToken } from "@/lib/api";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    if (getAccessToken() === null) {
      router.replace("/login");
      return;
    }
    setAllowed(true);
  }, [router]);

  if (!allowed) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <p className="text-sm text-zinc-500">Loading...</p>
      </main>
    );
  }

  return children;
}
