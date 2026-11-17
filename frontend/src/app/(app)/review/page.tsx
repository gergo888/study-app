"use client";

import { useQuery } from "@tanstack/react-query";

import { ErrorAlert, Loader } from "@/components/common/ui";
import { PracticeRunner } from "@/components/practice/PracticeRunner";
import { api } from "@/lib/api";
import type { PracticeItem } from "@/lib/types";

export default function ReviewPage() {
  const { data, error, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ["session", "due"],
    queryFn: () => api<{ items: PracticeItem[] }>("/practice/session/?due=1&limit=100"),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: "always",
  });
  if (isLoading) return <Loader label="Collecting due cards…" />;
  if (error || !data) return <ErrorAlert error={error} />;
  return (
    <>
      <div className="practice-wrap mb-3">
        <h1 className="page-title">Review</h1>
        <p className="text-secondary mb-0">
          Spaced repetition: flashcards and quiz questions whose review date has come, across all materials.
        </p>
      </div>
      <PracticeRunner key={dataUpdatedAt} items={data.items} context="review" backHref="/" title="Due reviews" />
    </>
  );
}
