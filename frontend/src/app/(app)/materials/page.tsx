"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Modal from "react-bootstrap/Modal";

import { ErrorAlert, Loader } from "@/components/common/ui";
import { api } from "@/lib/api";
import { useMaterials } from "@/lib/queries";
import type { Material } from "@/lib/types";

function NewMaterialModal({ show, onHide }: { show: boolean; onHide: () => void }) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const m = await api<Material>("/materials/", { body: { title, description } });
      router.push(`/materials/${m.slug}?tab=pdf`);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  };
  return (
    <Modal show={show} onHide={onHide} centered>
      <form onSubmit={submit}>
        <Modal.Header closeButton>
          <Modal.Title className="h5">New study material</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <ErrorAlert error={error} />
          <label className="form-label small fw-semibold">Title</label>
          <input className="form-control mb-3" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Network+ N10-009" required autoFocus />
          <label className="form-label small fw-semibold">Description</label>
          <textarea className="form-control" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
          <p className="small text-secondary mt-3 mb-0">Next step: import the PDF. Chapters are built from its outline.</p>
        </Modal.Body>
        <Modal.Footer>
          <button type="button" className="btn btn-light" onClick={onHide}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={busy || !title.trim()}>
            Create
          </button>
        </Modal.Footer>
      </form>
    </Modal>
  );
}

export default function MaterialsPage() {
  const { data, error, isLoading } = useMaterials();
  const [show, setShow] = useState(false);
  return (
    <>
      <div className="d-flex flex-wrap justify-content-between align-items-end gap-3 mb-4">
        <div>
          <h1 className="page-title">Study materials</h1>
          <p className="text-secondary mb-0">Each material has a PDF, a study plan and notes.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShow(true)}>
          <i className="bi bi-plus-lg me-1" />
          New material
        </button>
      </div>
      {isLoading && <Loader />}
      <ErrorAlert error={error} />
      {data?.length === 0 && (
        <div className="card">
          <div className="empty-state">
            <i className="bi bi-collection" />
            No materials yet. Create one and import its PDF.
          </div>
        </div>
      )}
      <div className="row g-3">
        {data?.map((m) => {
          const learned = m.status_counts.learned ?? 0;
          const pct = m.chapters_total ? Math.round((learned / m.chapters_total) * 100) : 0;
          return (
            <div className="col-md-6 col-xl-4" key={m.slug}>
              <Link href={`/materials/${m.slug}`} className="card h-100 text-decoration-none text-reset">
                <div className="card-body d-flex flex-column gap-2">
                  <div className="d-flex gap-3 align-items-start">
                    <span className="doc-icon">
                      <i className="bi bi-journal-bookmark" />
                    </span>
                    <div className="min-w-0">
                      <div className="fw-semibold">{m.title}</div>
                      <div className="small text-secondary text-truncate">{m.description || (m.has_pdf ? m.pdf_name : "No PDF yet")}</div>
                    </div>
                  </div>
                  <div className="small text-secondary mt-auto">
                    {m.chapters_total} chapters · {m.page_count} pages
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    <div className="progress flex-grow-1" style={{ height: 6 }}>
                      <div className="progress-bar bg-success" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="small fw-semibold">{pct}%</span>
                  </div>
                </div>
              </Link>
            </div>
          );
        })}
      </div>
      <NewMaterialModal show={show} onHide={() => setShow(false)} />
    </>
  );
}
