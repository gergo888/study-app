"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorAlert, Loader, Md } from "@/components/common/ui";
import { MarkdownEditor } from "@/components/editor/MarkdownEditor";
import { api } from "@/lib/api";
import { qk, useNotes } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { NoteSummary } from "@/lib/types";

function NoteForm({ slug, note, onDeleted }: { slug: string; note: NoteSummary; onDeleted: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [title, setTitle] = useState(note.title);
  const [body, setBody] = useState(note.body ?? "");
  const [preview, setPreview] = useState(false);
  const [saveError, setSaveError] = useState<unknown>(null);
  const dirty = title !== note.title || body !== (note.body ?? "");

  const save = async () => {
    setSaveError(null);
    try {
      const saved = await api<NoteSummary>(`/materials/${slug}/notes/${note.id}/`, { method: "PUT", body: { title, body, base_sha: note.sha } });
      qc.setQueryData(qk.note(slug, note.id), saved);
      qc.invalidateQueries({ queryKey: qk.notes(slug) });
      toast("Note saved", "success");
    } catch (e) {
      setSaveError(e);
    }
  };
  const remove = async () => {
    if (!window.confirm("Delete this note?")) return;
    await api(`/materials/${slug}/notes/${note.id}/`, { method: "DELETE" });
    qc.invalidateQueries({ queryKey: qk.notes(slug) });
    onDeleted();
  };

  return (
    <div className="card">
      <div className="card-body">
        <ErrorAlert error={saveError} />
        <div className="d-flex gap-2 mb-3">
          <input className="form-control fw-semibold" value={title} onChange={(e) => setTitle(e.target.value)} />
          <div className="seg">
            <button aria-pressed={!preview} onClick={() => setPreview(false)}>
              Write
            </button>
            <button aria-pressed={preview} onClick={() => setPreview(true)}>
              Preview
            </button>
          </div>
        </div>
        {preview ? (
          <div className="md-preview">
            <Md text={body || "_Empty note_"} />
          </div>
        ) : (
          <MarkdownEditor value={body} onChange={setBody} height="420px" />
        )}
        <div className="d-flex justify-content-between mt-3">
          <button className="btn btn-outline-danger btn-sm" onClick={remove}>
            <i className="bi bi-trash me-1" />
            Delete
          </button>
          <button className="btn btn-primary" onClick={save} disabled={!dirty}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

function NoteEditor({ slug, id, onDeleted }: { slug: string; id: string; onDeleted: () => void }) {
  const { data, isLoading, error } = useQuery({ queryKey: qk.note(slug, id), queryFn: () => api<NoteSummary>(`/materials/${slug}/notes/${id}/`) });
  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;
  return <NoteForm key={data.sha} slug={slug} note={data} onDeleted={onDeleted} />;
}

export function MaterialNotes({ slug }: { slug: string }) {
  const qc = useQueryClient();
  const { data, isLoading, error } = useNotes(slug);
  const [active, setActive] = useState<string | null>(null);
  const create = async () => {
    const title = window.prompt("Note title", "New note");
    if (!title) return;
    const note = await api<NoteSummary>(`/materials/${slug}/notes/`, { body: { title, body: "" } });
    await qc.invalidateQueries({ queryKey: qk.notes(slug) });
    setActive(note.id);
  };
  const current = active ?? data?.[0]?.id ?? null;
  return (
    <div className="row g-3">
      <div className="col-lg-4">
        <div className="card">
          <div className="card-header d-flex justify-content-between align-items-center">
            <h2 className="h6 mb-0">Notes</h2>
            <button className="btn btn-sm btn-primary" onClick={create}>
              <i className="bi bi-plus-lg" /> New
            </button>
          </div>
          <div className="card-body pt-2">
            {isLoading && <Loader />}
            <ErrorAlert error={error} />
            {data?.length === 0 && <div className="small text-secondary">No notes yet. They are saved as Markdown files next to the content.</div>}
            <div className="list-group list-group-flush">
              {data?.map((n) => (
                <button key={n.id} className={`list-group-item list-group-item-action ${n.id === current ? "active" : ""}`} onClick={() => setActive(n.id)}>
                  <div className="fw-semibold">{n.title}</div>
                  <div className="small opacity-75 text-truncate">{n.excerpt || "—"}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="col-lg-8">{current && <NoteEditor key={current} slug={slug} id={current} onDeleted={() => setActive(null)} />}</div>
    </div>
  );
}
