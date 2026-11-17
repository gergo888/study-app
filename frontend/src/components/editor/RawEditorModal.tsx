"use client";

import { useState } from "react";
import Modal from "react-bootstrap/Modal";

import { ErrorAlert, IssueList, Loader } from "@/components/common/ui";
import { api, ApiError, issuesOf } from "@/lib/api";
import { useInvalidateChapter, useRawDoc } from "@/lib/queries";
import { useToast } from "@/lib/toast";
import type { Issue, RawDoc } from "@/lib/types";

import { MarkdownEditor } from "./MarkdownEditor";

const FILE = { summary: "summary.md", flashcards: "flashcards.md", quiz: "quiz.md", notes: "notes.md" } as const;
type Kind = keyof typeof FILE;

function RawEditorBody({
  doc,
  slug,
  chapterKey,
  kind,
  onHide,
  onReload,
}: {
  doc: RawDoc;
  slug: string;
  chapterKey: string;
  kind: Kind;
  onHide: () => void;
  onReload: () => void;
}) {
  const invalidate = useInvalidateChapter();
  const toast = useToast();
  const [text, setText] = useState(doc.text);
  const [issues, setIssues] = useState<Issue[]>(doc.issues);
  const [saveError, setSaveError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    setSaveError(null);
    try {
      await api<{ sha: string; issues: Issue[] }>(`/chapters/${slug}/${chapterKey}/documents/${kind}/`, {
        method: "PUT",
        body: { text, base_sha: doc.sha },
      });
      invalidate(slug, chapterKey);
      toast(`${FILE[kind]} saved`, "success");
      onHide();
    } catch (e) {
      const found = issuesOf(e);
      if (found.length) setIssues(found);
      setSaveError(
        e instanceof ApiError && e.status === 409
          ? new Error("The file changed on disk (maybe Claude Code edited it). Reload to get the latest version — your edits here are not saved.")
          : e,
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Modal.Body>
        <ErrorAlert error={saveError} />
        <p className="small text-secondary">
          Format: see <code>docs/CONTENT_FORMAT.md</code>. Keep the <code>{"{#id}"}</code> markers stable — progress and spaced repetition are attached to them.
        </p>
        <MarkdownEditor value={text} onChange={setText} />
        <div className="mt-2">
          <IssueList issues={issues} />
        </div>
      </Modal.Body>
      <Modal.Footer>
        <button className="btn btn-light me-auto" onClick={onReload}>
          <i className="bi bi-arrow-clockwise me-1" />
          Reload from disk
        </button>
        <button className="btn btn-light" onClick={onHide}>
          Cancel
        </button>
        <button className="btn btn-primary" onClick={save} disabled={busy || text === doc.text}>
          Save
        </button>
      </Modal.Footer>
    </>
  );
}

export function RawEditorModal({ show, onHide, slug, chapterKey, kind }: { show: boolean; onHide: () => void; slug: string; chapterKey: string; kind: Kind }) {
  const { data, isLoading, error, refetch, dataUpdatedAt } = useRawDoc(slug, chapterKey, kind, show);
  return (
    <Modal show={show} onHide={onHide} size="xl" centered backdrop="static">
      <Modal.Header closeButton>
        <Modal.Title className="h5">
          <i className="bi bi-markdown me-2" />
          Edit {FILE[kind]}
        </Modal.Title>
      </Modal.Header>
      {isLoading && (
        <Modal.Body>
          <Loader />
        </Modal.Body>
      )}
      {error && (
        <Modal.Body>
          <ErrorAlert error={error} />
        </Modal.Body>
      )}
      {data && show && (
        <RawEditorBody key={`${data.sha}-${dataUpdatedAt}`} doc={data} slug={slug} chapterKey={chapterKey} kind={kind} onHide={onHide} onReload={() => refetch()} />
      )}
    </Modal>
  );
}
