"use client";

import { createContext, useCallback, useContext, useState } from "react";

type Toast = { id: number; text: string; tone: "xp" | "info" | "error" | "success" };

const ToastContext = createContext<(text: string, tone?: Toast["tone"]) => void>(() => {});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), tone === "error" ? 6000 : 2600);
  }, []);
  const icon = { xp: "bi-stars text-warning", info: "bi-info-circle text-info", error: "bi-exclamation-triangle text-danger", success: "bi-check-circle text-success" };
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="xp-toast" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id}>
            <i className={`bi ${icon[t.tone]} me-2`} />
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
