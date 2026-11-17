"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";

import { ErrorAlert, Loader, Md } from "@/components/common/ui";
import { useChapter, useSummary } from "@/lib/queries";

type PrintLang = "en" | "hu" | "both";

export default function PrintSummaryPage() {
  const { material, key } = useParams<{ material: string; key: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const lang = (params.get("lang") as PrintLang) || "both";
  const chapter = useChapter(material, key);
  const summary = useSummary(material, key);

  if (chapter.isLoading || summary.isLoading) return <Loader />;
  if (chapter.error || summary.error || !chapter.data || !summary.data) return <ErrorAlert error={chapter.error || summary.error} />;
  const c = chapter.data;
  const s = summary.data;
  const en = lang !== "hu";
  const hu = lang !== "en";
  const title = String(lang === "hu" ? s.meta.title_hu ?? c.title : c.title);

  return (
    <div style={{ background: "#fff", minHeight: "100vh" }} data-bs-theme="light">
      <div className="print-actions">
        <div className="seg me-auto">
          {(["en", "hu", "both"] as PrintLang[]).map((l) => (
            <button key={l} aria-pressed={lang === l} onClick={() => router.replace(`?lang=${l}`)}>
              {l === "both" ? "EN+HU" : l.toUpperCase()}
            </button>
          ))}
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => window.print()}>
          <i className="bi bi-printer me-1" />
          Print / Save as PDF
        </button>
      </div>
      <article className="print-page">
        <h1>
          {c.code ? `${c.code} · ` : ""}
          {title}
        </h1>
        <div className="meta">
          {c.material_title} · {c.group_title}
          {c.group_subtitle ? ` · ${c.group_subtitle}` : ""} · PDF pp. {c.start_page}–{c.end_page}
        </div>
        {s.sections.map((sec) => (
          <section key={sec.key}>
            <h2>
              {en ? sec.heading_en : sec.heading_hu}
              {en && hu && sec.heading_hu !== sec.heading_en && <span className="hu">{sec.heading_hu}</span>}
            </h2>
            {sec.points.map((p) => (
              <div className="print-point" key={p.key}>
                <div className="t">
                  {en ? p.title_en : p.title_hu}
                  {en && hu && p.title_hu !== p.title_en && <span className="hu fw-normal"> — {p.title_hu}</span>}
                </div>
                {en && <Md text={p.body_en} />}
                {hu && (
                  <div className={en ? "hu" : ""}>
                    <Md text={p.body_hu} />
                  </div>
                )}
                {p.figure && (
                  <figure>
                    {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                    <img src={p.figure.url} alt={p.figure.caption_en} />
                    <figcaption>{lang === "hu" ? p.figure.caption_hu : lang === "en" ? p.figure.caption_en : `${p.figure.caption_en}${p.figure.caption_hu !== p.figure.caption_en ? ` · ${p.figure.caption_hu}` : ""}`}</figcaption>
                  </figure>
                )}
              </div>
            ))}
          </section>
        ))}
      </article>
    </div>
  );
}
