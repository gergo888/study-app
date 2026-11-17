"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import Modal from "react-bootstrap/Modal";

import { ErrorAlert, Loader } from "@/components/common/ui";
import { api } from "@/lib/api";
import { qk, useFigures } from "@/lib/queries";

type Picked = { path: string; url: string; caption: string };

export function FigurePicker({
  show,
  slug,
  chapterKey,
  onHide,
  onPick,
}: {
  show: boolean;
  slug: string;
  chapterKey: string;
  onHide: () => void;
  onPick: (f: Picked) => void;
}) {
  const qc = useQueryClient();
  const { data, isLoading, error } = useFigures(slug, chapterKey, show);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);

  const adopt = async (candidateKey: string) => {
    setBusy(true);
    try {
      const res = await api<Picked>(`/chapters/${slug}/${chapterKey}/figures/`, { body: { action: "adopt", key: candidateKey } });
      await qc.invalidateQueries({ queryKey: qk.figures(slug, chapterKey) });
      onPick(res);
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };
  const extract = async () => {
    setBusy(true);
    try {
      await api(`/chapters/${slug}/${chapterKey}/figures/`, { body: { action: "extract" } });
      await qc.invalidateQueries({ queryKey: qk.figures(slug, chapterKey) });
    } catch (e) {
      setErr(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal show={show} onHide={onHide} size="xl" centered scrollable>
      <Modal.Header closeButton>
        <Modal.Title className="h5">Choose a figure</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <ErrorAlert error={error || err} />
        {isLoading && <Loader />}
        {data && (
          <>
            {!!data.adopted.length && (
              <>
                <h3 className="h6">Used in this chapter</h3>
                <div className="figure-grid mb-4">
                  {data.adopted.map((f) => (
                    <button key={f.path} type="button" onClick={() => onPick({ path: f.path, url: f.url, caption: f.caption })}>
                      {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                      <img src={f.url} alt="" loading="lazy" />
                      <div className="text-truncate mt-1">{f.caption || f.path}</div>
                    </button>
                  ))}
                </div>
              </>
            )}
            <div className="d-flex justify-content-between align-items-center mb-2">
              <h3 className="h6 mb-0">Figures found in the PDF chapter</h3>
              <button className="btn btn-sm btn-soft" onClick={extract} disabled={busy}>
                <i className="bi bi-arrow-clockwise me-1" />
                {data.candidates.length ? "Re-extract" : "Extract from PDF"}
              </button>
            </div>
            {!data.candidates.length && <div className="small text-secondary">No candidates extracted yet.</div>}
            <div className="figure-grid">
              {data.candidates
                .filter((c) => !c.adopted)
                .map((c) => (
                  <button key={c.key} type="button" disabled={busy} onClick={() => adopt(c.key)}>
                    {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image */}
                    <img src={c.url} alt="" loading="lazy" />
                    <div className="text-truncate mt-1">
                      p.{c.page} {c.caption}
                    </div>
                  </button>
                ))}
            </div>
          </>
        )}
      </Modal.Body>
    </Modal>
  );
}
