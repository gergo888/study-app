"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./api";
import type {
  CardsResponse,
  ChapterDetail,
  Dashboard,
  FiguresResponse,
  Flashcard,
  Material,
  MaterialDetail,
  NoteSummary,
  OutlineInfo,
  QuizQuestion,
  RawDoc,
  SummaryResponse,
} from "./types";

export const qk = {
  materials: ["materials"] as const,
  material: (slug: string) => ["material", slug] as const,
  outline: (slug: string) => ["outline", slug] as const,
  chapter: (slug: string, key: string) => ["chapter", slug, key] as const,
  summary: (slug: string, key: string) => ["summary", slug, key] as const,
  cards: (slug: string, key: string, kind: "flashcards" | "quiz") => ["cards", slug, key, kind] as const,
  raw: (slug: string, key: string, kind: string) => ["raw", slug, key, kind] as const,
  figures: (slug: string, key: string) => ["figures", slug, key] as const,
  notes: (slug: string) => ["notes", slug] as const,
  note: (slug: string, id: string) => ["note", slug, id] as const,
  dashboard: ["dashboard"] as const,
};

export const useMaterials = () => useQuery({ queryKey: qk.materials, queryFn: () => api<Material[]>("/materials/") });
export const useMaterial = (slug: string) =>
  useQuery({ queryKey: qk.material(slug), queryFn: () => api<MaterialDetail>(`/materials/${slug}/`) });
export const useOutline = (slug: string, enabled = true) =>
  useQuery({ queryKey: qk.outline(slug), queryFn: () => api<OutlineInfo>(`/materials/${slug}/outline/`), enabled });
export const useChapter = (slug: string, key: string) =>
  useQuery({ queryKey: qk.chapter(slug, key), queryFn: () => api<ChapterDetail>(`/chapters/${slug}/${key}/`) });
export const useSummary = (slug: string, key: string) =>
  useQuery({ queryKey: qk.summary(slug, key), queryFn: () => api<SummaryResponse>(`/chapters/${slug}/${key}/summary/`) });
export const useFlashcards = (slug: string, key: string) =>
  useQuery({
    queryKey: qk.cards(slug, key, "flashcards"),
    queryFn: () => api<CardsResponse<Flashcard>>(`/chapters/${slug}/${key}/flashcards/`),
  });
export const useQuiz = (slug: string, key: string) =>
  useQuery({
    queryKey: qk.cards(slug, key, "quiz"),
    queryFn: () => api<CardsResponse<QuizQuestion>>(`/chapters/${slug}/${key}/quiz/`),
  });
export const useRawDoc = (slug: string, key: string, kind: string, enabled = true) =>
  useQuery({ queryKey: qk.raw(slug, key, kind), queryFn: () => api<RawDoc>(`/chapters/${slug}/${key}/documents/${kind}/`), enabled });
export const useFigures = (slug: string, key: string, enabled = true) =>
  useQuery({ queryKey: qk.figures(slug, key), queryFn: () => api<FiguresResponse>(`/chapters/${slug}/${key}/figures/`), enabled });
export const useNotes = (slug: string) =>
  useQuery({ queryKey: qk.notes(slug), queryFn: () => api<NoteSummary[]>(`/materials/${slug}/notes/`) });
export const useDashboard = () => useQuery({ queryKey: qk.dashboard, queryFn: () => api<Dashboard>("/stats/dashboard/") });

/** Invalidate everything that depends on a chapter's documents or progress. */
export function useInvalidateChapter() {
  const qc = useQueryClient();
  return (slug: string, key: string) => {
    qc.invalidateQueries({ queryKey: qk.chapter(slug, key) });
    qc.invalidateQueries({ queryKey: qk.summary(slug, key) });
    qc.invalidateQueries({ queryKey: ["cards", slug, key] });
    qc.invalidateQueries({ queryKey: ["raw", slug, key] });
    qc.invalidateQueries({ queryKey: qk.material(slug) });
    qc.invalidateQueries({ queryKey: qk.materials });
    qc.invalidateQueries({ queryKey: qk.dashboard });
  };
}

export function useSummaryOp(slug: string, key: string) {
  const invalidate = useInvalidateChapter();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<{ sha: string; key?: string }>(`/chapters/${slug}/${key}/summary/`, { body }),
    onSettled: () => invalidate(slug, key),
  });
}

export function useCardOp(slug: string, key: string, kind: "flashcards" | "quiz") {
  const invalidate = useInvalidateChapter();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api<{ sha: string; key?: string }>(`/chapters/${slug}/${key}/${kind}/`, { body }),
    onSettled: () => invalidate(slug, key),
  });
}

export function useSetChapterStatus(slug: string, key: string) {
  const invalidate = useInvalidateChapter();
  return useMutation({
    mutationFn: (status: string) => api(`/chapters/${slug}/${key}/`, { method: "PATCH", body: { status } }),
    onSettled: () => invalidate(slug, key),
  });
}
