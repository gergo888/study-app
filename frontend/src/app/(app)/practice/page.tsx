"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";

import { ErrorAlert, Loader } from "@/components/common/ui";
import { PracticeRunner } from "@/components/practice/PracticeRunner";
import { api } from "@/lib/api";
import type { PracticeItem } from "@/lib/types";

const TITLES: Record<string, string> = { flashcards: "Flashcards", quiz: "Quiz", write: "Write it out" };

export default function PracticePage() {
  const params = useSearchParams();
  const qs = params.toString();
  const mode = params.get("mode") ?? "flashcards";
  const material = params.get("material") ?? "";
  const chapter = params.get("chapter") ?? "";
  const selected = (params.get("points") ?? "").split(",").filter(Boolean).length;
  const { data, error, isLoading } = useQuery({
    queryKey: ["session", qs],
    queryFn: () => api<{ items: PracticeItem[] }>(`/practice/session/?${qs}`),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: "always",
  });
  if (isLoading) return <Loader label="Preparing your session…" />;
  if (error || !data) return <ErrorAlert error={error} />;
  const title = `${TITLES[mode] ?? mode} · ${chapter}${selected ? ` · ${selected} selected points` : ""}`;
  const back = `/chapters/${material}/${chapter}?step=${mode === "write" ? "summary" : mode}`;
  return <PracticeRunner key={qs} items={data.items} context="learn" backHref={back} title={title} />;
}
