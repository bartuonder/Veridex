"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/auth/session")
      .then((response) => response.json())
      .then((data: { ok?: boolean }) => {
        if (cancelled) {
          return;
        }
        if (!data.ok) {
          router.replace("/login");
          return;
        }
        setAllowed(true);
      })
      .catch(() => {
        if (!cancelled) {
          router.replace("/login");
        }
      });
    return () => {
      cancelled = true;
    };
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
