"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import { ErrorAlert, Loader } from "@/components/common/ui";
import { MaterialNotes } from "@/components/notes/MaterialNotes";
import { PdfTab } from "@/components/plan/PdfTab";
import { StudyPlan } from "@/components/plan/StudyPlan";
import { useMaterial } from "@/lib/queries";

const TABS = [
  { id: "plan", label: "Study plan", icon: "bi-calendar-week" },
  { id: "pdf", label: "PDF & chapters", icon: "bi-file-earmark-pdf" },
  { id: "notes", label: "Notes", icon: "bi-journal-text" },
] as const;

export default function MaterialPage() {
  const { slug } = useParams<{ slug: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const tab = (params.get("tab") as (typeof TABS)[number]["id"]) || "plan";
  const { data, error, isLoading } = useMaterial(slug);

  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;
  const next = data.plan_status.next_chapter;

  return (
    <>
      <nav className="small mb-2">
        <Link href="/materials" className="text-decoration-none">
          Study materials
        </Link>
      </nav>
      <div className="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-3">
        <div className="min-w-0">
          <h1 className="page-title">{data.title}</h1>
          {data.description && <p className="text-secondary mb-0">{data.description}</p>}
        </div>
        {next && (
          <Link href={`/chapters/${slug}/${next}`} className="btn btn-primary">
            <i className="bi bi-play-fill me-1" />
            Continue with {next}
          </Link>
        )}
      </div>
      <ul className="nav nav-underline mb-3">
        {TABS.map((t) => (
          <li className="nav-item" key={t.id}>
            <button className={`nav-link ${tab === t.id ? "active" : ""}`} onClick={() => router.replace(`/materials/${slug}?tab=${t.id}`, { scroll: false })}>
              <i className={`bi ${t.icon} me-1`} />
              {t.label}
            </button>
          </li>
        ))}
      </ul>
      {tab === "plan" && <StudyPlan material={data} />}
      {tab === "pdf" && <PdfTab material={data} />}
      {tab === "notes" && <MaterialNotes slug={slug} />}
    </>
  );
}
