"use client";

// Per-browser preferences: content language (EN / HU / both) and light/dark theme.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Lang = "en" | "hu" | "both";
export type Theme = "light" | "dark";

interface Prefs {
  lang: Lang;
  setLang: (l: Lang) => void;
  /** Language used for single-language interactions (memorize, write check). */
  primary: "en" | "hu";
  theme: Theme;
  setTheme: (t: Theme) => void;
}

const PrefsContext = createContext<Prefs | null>(null);

function read<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const v = localStorage.getItem(key) as T | null;
    return v && allowed.includes(v) ? v : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode) */
  }
}

export function PrefsProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => read("lang", ["en", "hu", "both"] as const, "both"));
  const [theme, setThemeState] = useState<Theme>(() =>
    read("theme", ["light", "dark"] as const, window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-bs-theme", theme);
  }, [theme]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    write("lang", l);
  }, []);
  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    write("theme", t);
  }, []);

  const value = useMemo(
    () => ({ lang, setLang, primary: (lang === "hu" ? "hu" : "en") as "en" | "hu", theme, setTheme }),
    [lang, setLang, theme, setTheme],
  );
  return <PrefsContext.Provider value={value}>{children}</PrefsContext.Provider>;
}

export function usePrefs(): Prefs {
  const ctx = useContext(PrefsContext);
  if (!ctx) throw new Error("usePrefs outside PrefsProvider");
  return ctx;
}
