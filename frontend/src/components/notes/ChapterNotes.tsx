"use client";

import { useState } from "react";

import { ErrorAlert, Loader, Md } from "@/components/common/ui";
import { MarkdownEditor } from "@/components/editor/MarkdownEditor";
import { api } from "@/lib/api";
import { useRawDoc } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { RawDoc } from "@/lib/types";

/** Split off the YAML front matter so only the note body is edited. */
function splitFrontMatter(text: string): [string, string] {
  const m = text.match(/^---\n[\s\S]*?\n---\n\n?/);
  return m ? [m[0], text.slice(m[0].length)] : ["", text];
}

function NotesEditor({ doc, slug, chapterKey, onSaved }: { doc: RawDoc; slug: string; chapterKey: string; onSaved: () => void }) {
  const toast = useToast();
  const [front, initialBody] = splitFrontMatter(doc.text);
  const [body, setBody] = useState(initialBody);
  const [preview, setPreview] = useState(false);
  const [saveError, setSaveError] = useState<unknown>(null);

  const save = async () => {
    setSaveError(null);
    try {
      await api(`/chapters/${slug}/${chapterKey}/documents/notes/`, { method: "PUT", body: { text: front + body, base_sha: doc.sha } });
      onSaved();
      toast("Notes saved", "success");
    } catch (e) {
      setSaveError(e);
    }
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className="d-flex align-items-center mb-3">
          <div className="small text-secondary">
            Saved as <code>notes.md</code> next to the chapter&apos;s summary.
          </div>
          <div className="seg ms-auto">
            <button aria-pressed={!preview} onClick={() => setPreview(false)}>
              Write
            </button>
            <button aria-pressed={preview} onClick={() => setPreview(true)}>
              Preview
            </button>
          </div>
        </div>
        <ErrorAlert error={saveError} />
        {preview ? (
          <div className="md-preview">
            <Md text={body || "_No notes yet_"} />
          </div>
        ) : (
          <MarkdownEditor value={body} onChange={setBody} height="420px" />
        )}
        <div className="d-flex justify-content-end mt-3">
          <button className="btn btn-primary" onClick={save} disabled={body === initialBody}>
            Save notes
          </button>
        </div>
      </div>
    </div>
  );
}

export function ChapterNotes({ slug, chapterKey }: { slug: string; chapterKey: string }) {
  const { data, isLoading, error, refetch } = useRawDoc(slug, chapterKey, "notes");
  if (isLoading) return <Loader />;
  if (error || !data) return <ErrorAlert error={error} />;
  return <NotesEditor key={data.sha ?? "new"} doc={data} slug={slug} chapterKey={chapterKey} onSaved={() => refetch()} />;
}
