"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Suspense, use, useState } from "react";
import { browser } from "react-dom";

import { ApiError } from "@/lib/api";
import { PrefsProvider } from "@/lib/prefs";
import { ToastProvider } from "@/lib/toast";

function FullPageLoader() {
  return (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: "100vh" }}>
      <div className="spinner-border text-primary" role="status" aria-label="Loading" />
    </div>
  );
}

// Everything below is private, per-user and reads localStorage/cookies, so it
// renders in the browser only (no server prerender of user data).
function BrowserOnly({ children }: { children: React.ReactNode }) {
  use(browser("The app is private and reads browser-only preferences and session state."));
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 15_000,
            refetchOnWindowFocus: true,
            retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <PrefsProvider>
        <ToastProvider>{children}</ToastProvider>
      </PrefsProvider>
    </QueryClientProvider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<FullPageLoader />}>
      <BrowserOnly>{children}</BrowserOnly>
    </Suspense>
  );
}
