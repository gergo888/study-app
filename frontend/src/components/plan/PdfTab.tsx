"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorAlert, Loader } from "@/components/common/ui";
import { api, upload } from "@/lib/api";
import { qk, useOutline } from "@/lib/queries";
import type { MaterialDetail } from "@/lib/types";

export function PdfTab({ material }: { material: MaterialDetail }) {
  const qc = useQueryClient();
  const outline = useOutline(material.slug, material.has_pdf);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [rebuilding, setRebuilding] = useState(false);

  const refresh = async () => {
    await qc.invalidateQueries({ queryKey: qk.material(material.slug) });
    await qc.invalidateQueries({ queryKey: qk.outline(material.slug) });
    await qc.invalidateQueries({ queryKey: qk.materials });
  };

  const doUpload = async () => {
    if (!file) return;
    setError(null);
    setProgress(0);
    try {
      const form = new FormData();
      form.append("file", file);
      await upload(`/materials/${material.slug}/pdf/`, form, setProgress);
      setFile(null);
      await refresh();
    } catch (e) {
      setError(e);
    } finally {
      setProgress(null);
    }
  };

  const rebuild = async (level: number) => {
    if (!window.confirm(`Rebuild chapters from outline level ${level}? Progress is kept for chapters whose key stays the same.`)) return;
    setRebuilding(true);
    try {
      await api(`/materials/${material.slug}/chapters/build/`, { body: { level } });
      await refresh();
    } catch (e) {
      setError(e);
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div className="row g-3">
      <div className="col-lg-6">
        <div className="card h-100">
          <div className="card-header">
            <h2 className="h6 mb-0">PDF</h2>
            <small className="text-secondary">Stored on the server; chapters are sliced from it for reading.</small>
          </div>
          <div className="card-body">
            <ErrorAlert error={error} />
            {material.has_pdf ? (
              <div className="d-flex align-items-center gap-3 mb-3">
                <span className="doc-icon">
                  <i className="bi bi-file-earmark-pdf" />
                </span>
                <div className="flex-grow-1 min-w-0">
                  <div className="fw-semibold text-truncate">{material.pdf_name}</div>
                  <div className="small text-secondary">{material.page_count} pages</div>
                </div>
                <a className="btn btn-sm btn-outline-primary" href={`/api/materials/${material.slug}/pdf/`} target="_blank" rel="noreferrer">
                  Open
                </a>
              </div>
            ) : (
              <p className="text-secondary small">No PDF yet.</p>
            )}
            <label className="form-label small fw-semibold">{material.has_pdf ? "Replace PDF" : "Import PDF"}</label>
            <div className="d-flex gap-2">
              <input type="file" accept="application/pdf" className="form-control" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              <button className="btn btn-primary" onClick={doUpload} disabled={!file || progress !== null}>
                Upload
              </button>
            </div>
            {progress !== null && (
              <div className="mt-3">
                <div className="progress" style={{ height: 8 }}>
                  <div className="progress-bar progress-bar-striped progress-bar-animated" style={{ width: `${progress}%` }} />
                </div>
                <div className="small text-secondary mt-1">{progress < 100 ? `Uploading… ${progress}%` : "Reading the outline…"}</div>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="col-lg-6">
        <div className="card h-100">
          <div className="card-header">
            <h2 className="h6 mb-0">Chapters from the outline</h2>
            <small className="text-secondary">Pick which outline level counts as one chapter.</small>
          </div>
          <div className="card-body">
            {!material.has_pdf && <p className="text-secondary small mb-0">Import a PDF first.</p>}
            {outline.isLoading && <Loader />}
            {outline.data && (
              <div className="table-responsive">
                <table className="table align-middle">
                  <thead>
                    <tr>
                      <th>Level</th>
                      <th>Chapters</th>
                      <th>Avg. pages</th>
                      <th>Examples</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {outline.data.levels.map((l) => (
                      <tr key={l.level}>
                        <td>
                          {l.level}
                          {l.level === outline.data.suggested_level && <span className="badge-soft b-info no-dot ms-2">suggested</span>}
                        </td>
                        <td>{l.chapters}</td>
                        <td>{l.avg_pages}</td>
                        <td className="small text-secondary" style={{ maxWidth: 220 }}>
                          <div className="text-truncate">{l.examples.join(" · ")}</div>
                        </td>
                        <td className="text-end">
                          {l.level === material.chapter_level ? (
                            <span className="badge-soft b-success">in use</span>
                          ) : (
                            <button className="btn btn-sm btn-soft" disabled={rebuilding} onClick={() => rebuild(l.level)}>
                              Use
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
