// Shapes returned by the Django API (see backend/apps/*/views.py).

export type ChapterStatus = "not_started" | "reading" | "read" | "learned";
export type ActivityResult = "correct" | "partial" | "wrong" | "seen";

export interface Material {
  slug: string;
  title: string;
  description: string;
  has_pdf: boolean;
  pdf_name: string;
  page_count: number;
  chapter_level: number;
  chapters_total: number;
  status_counts: Record<ChapterStatus, number>;
  plan: { start: string | null; target: string | null; weekdays: number[] };
  created_at: string;
}

export interface Chapter {
  material: string;
  key: string;
  order: number;
  code: string;
  title: string;
  group_title: string;
  group_subtitle: string;
  start_page: number;
  end_page: number;
  pages: number;
  status: ChapterStatus;
  read_at: string | null;
  learned_at: string | null;
  learned_via: string;
  has_content: boolean;
  docs: { summary: boolean; flashcards: boolean; quiz: boolean };
  scheduled_date: string | null;
}

export interface PlanStatus {
  has_plan: boolean;
  total: number;
  learned: number;
  scheduled_by_today: number;
  behind: number;
  on_track: boolean;
  next_chapter: string | null;
  items?: Record<string, string>;
}

export interface MaterialDetail extends Material {
  chapters: Chapter[];
  plan_status: PlanStatus;
}

export interface Health {
  stale: { kind: "flashcard" | "quiz"; card_key: string; point_key: string }[];
  missing: Record<string, ("flashcard" | "quiz")[]>;
  orphans: { kind: string; card_key: string; point_key: string }[];
}

export interface ChapterDetail extends Chapter {
  material_title: string;
  prev: string | null;
  next: string | null;
  pdf_url: string;
  counts: { points: number; flashcards: number; quiz: number; stale: number; missing: number };
  health: Health;
}

export interface Figure {
  path: string;
  url: string;
  caption_en: string;
  caption_hu: string;
}

export interface Point {
  key: string;
  title_en: string;
  title_hu: string;
  body_en: string;
  body_hu: string;
  concepts: string[][];
  figure: Figure | null;
}

export interface SummaryPoint extends Point {
  stale: boolean;
  missing: string[];
  progress: Partial<Record<"flashcard" | "quiz" | "reveal" | "write", { result: ActivityResult; ts: string }>>;
}

export interface Section {
  key: string;
  heading_en: string;
  heading_hu: string;
  points: SummaryPoint[];
}

export interface Issue {
  doc: string;
  line: number;
  message: string;
  severity: "error" | "warning";
}

export interface SummaryResponse {
  exists: boolean;
  sha: string | null;
  meta: Record<string, unknown>;
  sections: Section[];
  issues: Issue[];
  health: Health;
}

export interface SrsInfo {
  reps: number;
  lapses: number;
  due: string | null;
  last_review: string | null;
}

export interface Flashcard {
  key: string;
  point_key: string;
  front_en: string;
  front_hu: string;
  back_en: string;
  back_hu: string;
  figure: Figure | null;
  stale: boolean;
  srs: SrsInfo | null;
}

export interface QuizQuestion {
  key: string;
  point_key: string;
  question_en: string;
  question_hu: string;
  options: { en: string; hu: string }[];
  correct_index: number;
  why_en: string;
  why_hu: string;
  figure: Figure | null;
  stale: boolean;
  srs: SrsInfo | null;
}

export interface CardsResponse<T> {
  exists: boolean;
  sha: string | null;
  items: T[];
  issues: Issue[];
}

export interface RawDoc {
  exists: boolean;
  sha: string | null;
  text: string;
  issues: Issue[];
}

interface PracticeBase {
  material: string;
  chapter: string;
  chapter_title: string;
  key: string;
  point_key: string;
  point_title_en: string;
  point_title_hu: string;
  section_en: string;
  section_hu: string;
}
export type PracticeItem =
  | (PracticeBase & { kind: "flashcard"; data: Flashcard })
  | (PracticeBase & { kind: "quiz"; data: QuizQuestion })
  | (PracticeBase & { kind: "write"; data: Point });

export interface AnswerResult {
  correct: boolean;
  xp_awarded: number;
  total_xp: number;
  due: string | null;
  chapter_learned: string | null;
  correct_index: number | null;
}

export interface CheckResult {
  score: number;
  verdict: "correct" | "partial" | "wrong";
  matched: string[][];
  missed: string[][];
  original: string;
}

export interface Dashboard {
  level: number;
  xp: number;
  level_floor: number;
  next_level_at: number;
  progress: number;
  xp_today: number;
  streak: number;
  reviews_today: number;
  due: { total: number; by_kind: Record<string, number>; by_material: Record<string, number> };
  chapters_total: number;
  chapters_learned: number;
  materials: number;
  xp_by_day: { date: string; xp: number }[];
  recent: {
    ts: string;
    material: string;
    chapter: string;
    chapter_title: string;
    point_key: string;
    kind: string;
    result: ActivityResult;
  }[];
  continue: {
    material: string;
    material_title: string;
    chapter: string;
    code: string;
    title: string;
    status: ChapterStatus;
    scheduled_date: string | null;
    behind: number;
    learned: number;
    total: number;
  }[];
  today: string;
}

export interface NoteSummary {
  id: string;
  title: string;
  created: string;
  updated: string;
  sha: string;
  excerpt?: string;
  body?: string;
}

export interface OutlineInfo {
  levels: { level: number; chapters: number; avg_pages: number; examples: string[] }[];
  suggested_level: number | null;
  current_level: number;
}

export interface FiguresResponse {
  adopted: { path: string; url: string; caption: string; page: number | null }[];
  candidates: { key: string; page: number; caption: string; file: string; url: string; adopted: boolean; width: number; height: number }[];
}
