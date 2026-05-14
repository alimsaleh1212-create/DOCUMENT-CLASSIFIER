import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Layout } from "../components/Layout";
import { LabelBadge } from "../components/LabelBadge";
import { Toast } from "../components/Toast";
import client from "../api/client";
import { getRole } from "../hooks/useAuth";
import type { PredictionOut } from "../api/types";
import { PREDICTION_LABELS, COMMENT_COLORS } from "../api/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fallbackDocName(pred: PredictionOut): string {
  return `DOC-${pred.document_id.slice(0, 8).toUpperCase()}`;
}

function displayName(pred: PredictionOut): string {
  return pred.document_name?.trim() || fallbackDocName(pred);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// ── Card preview image (auto-loads via authenticated proxy) ──────────────────

function DocPreviewImage({ prediction }: { prediction: PredictionOut }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let createdUrl: string | null = null;

    if (!prediction.overlay_url) {
      setError(true);
      return;
    }

    client.get(`/predictions/${prediction.id}/overlay`, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        createdUrl = URL.createObjectURL(res.data);
        setBlobUrl(createdUrl);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [prediction.id, prediction.overlay_url]);

  if (error) {
    return (
      <div style={{ textAlign: "center", color: "#7A8DAE" }}>
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" style={{ margin: "0 auto 0.5rem", opacity: 0.5 }}>
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 9h18M9 21V9" />
        </svg>
        <div style={{ fontSize: "13px" }}>Still processing</div>
      </div>
    );
  }

  if (!blobUrl) {
    return <div className="skeleton" style={{ width: "100%", height: "100%", borderRadius: 0 }} />;
  }

  return (
    <img
      src={blobUrl}
      alt={displayName(prediction)}
      style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
    />
  );
}

// ── Color dot ─────────────────────────────────────────────────────────────────

function ColorDot({ color, size = 10 }: { color: string | null; size?: number }) {
  if (!color) return null;
  const match = COMMENT_COLORS.find((c) => c.value === color);
  return (
    <span style={{
      display: "inline-block",
      width: `${size}px`, height: `${size}px`,
      borderRadius: "50%",
      background: match?.hex ?? "#888",
      flexShrink: 0,
    }} />
  );
}

// ── Confidence pill ───────────────────────────────────────────────────────────

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.9 ? "var(--success)" : value >= 0.7 ? "var(--accent)" : "var(--warning)";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "0.2rem 0.55rem",
      borderRadius: "5px",
      fontSize: "14px",
      fontFamily: "var(--font-mono)",
      fontWeight: 600,
      color,
      background: `${color}1a`,
      border: `1px solid ${color}30`,
    }}>
      {pct}%
    </span>
  );
}

// ── Latency pill ─────────────────────────────────────────────────────────────

function LatencyPill({ ms }: { ms: number | null }) {
  if (ms === null || ms === undefined) {
    return <span style={{ color: "var(--text-dim)", fontSize: "14px" }}>—</span>;
  }
  const color = ms < 500 ? "var(--success)" : ms < 1000 ? "var(--accent)" : "var(--warning)";
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: "14px", color, fontWeight: 500 }}>
      {ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`}
    </span>
  );
}

// ── Document viewer modal (loads image via authenticated fetch) ──────────────

function DocViewModal({ prediction, onClose }: { prediction: PredictionOut; onClose: () => void }) {
  const [imgBlobUrl, setImgBlobUrl] = useState<string | null>(null);
  const [imgError, setImgError] = useState<string | null>(null);
  const [imgLoading, setImgLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const blobUrlToRevoke: string | null = null;

    async function loadImage() {
      setImgLoading(true);
      setImgError(null);
      try {
        // Fetch the overlay through the API proxy with bearer auth.
        // Axios client carries auth interceptor, so use it.
        const res = await client.get(`/predictions/${prediction.id}/overlay`, {
          responseType: "blob",
        });
        if (cancelled) return;
        const url = URL.createObjectURL(res.data);
        setImgBlobUrl(url);
      } catch (err) {
        if (cancelled) return;
        const status = (err as { response?: { status?: number } })?.response?.status;
        if (status === 404) {
          setImgError("This document has no overlay yet — it may still be processing or skipped.");
        } else if (status === 503) {
          setImgError("Blob storage is not configured in this environment.");
        } else {
          setImgError("Could not load the document image. Check API logs.");
        }
      } finally {
        if (!cancelled) setImgLoading(false);
      }
    }

    loadImage();
    return () => {
      cancelled = true;
      if (blobUrlToRevoke) URL.revokeObjectURL(blobUrlToRevoke);
    };
  }, [prediction.id]);

  useEffect(() => {
    return () => {
      if (imgBlobUrl) URL.revokeObjectURL(imgBlobUrl);
    };
  }, [imgBlobUrl]);

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 300,
        background: "rgba(6,8,15,0.92)",
        backdropFilter: "blur(12px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "1rem",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="animate-fade-up"
        style={{
          width: "100%", maxWidth: "920px",
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
          boxShadow: "0 24px 80px rgba(0,0,0,0.6)",
          display: "flex", flexDirection: "column",
          maxHeight: "90vh",
        }}
      >
        {/* Header */}
        <div style={{
          padding: "1rem 1.25rem",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <ColorDot color={prediction.comment_color} size={12} />
            <h3 style={{ fontSize: "17px", margin: 0, fontFamily: "var(--font-display)", color: "#F4F9FF" }}>
              {displayName(prediction)}
            </h3>
            <LabelBadge label={prediction.label} />
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#E8F0FF", padding: "0.3rem" }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Body */}
        <div style={{ display: "flex", overflow: "auto", flex: 1 }}>
          {/* Metadata panel */}
          <div style={{
            flex: "0 0 240px",
            borderRight: "1px solid var(--border-subtle)",
            padding: "1.25rem",
            display: "flex", flexDirection: "column", gap: "1rem",
          }}>
            {[
              { label: "Confidence", value: <ConfidencePill value={prediction.top1_confidence} /> },
              { label: "Latency", value: <LatencyPill ms={prediction.latency_ms} /> },
              { label: "Classified", value: <span style={{ fontSize: "13px", color: "#C8D4EA" }}>{formatDate(prediction.created_at)}</span> },
              { label: "Batch", value: <code style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>{prediction.batch_id.slice(0, 8)}…</code> },
            ].map(({ label, value }) => (
              <div key={label}>
                <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "#7A8DAE", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "0.3rem", fontWeight: 600 }}>
                  {label}
                </div>
                {value}
              </div>
            ))}
            {prediction.comment && (
              <div>
                <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "#7A8DAE", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "0.4rem", fontWeight: 600 }}>
                  Note
                </div>
                <div style={{
                  padding: "0.5rem 0.6rem",
                  background: "var(--bg-raised)",
                  borderLeft: `3px solid ${COMMENT_COLORS.find(c => c.value === prediction.comment_color)?.hex ?? "var(--border)"}`,
                  borderRadius: "var(--radius)",
                  fontSize: "13px",
                  color: "#E8F0FF",
                  lineHeight: 1.5,
                }}>
                  {prediction.comment}
                </div>
              </div>
            )}
            {/* Top-5 */}
            <div>
              <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "#7A8DAE", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "0.5rem", fontWeight: 600 }}>
                Top-5
              </div>
              {prediction.top5.slice(0, 5).map(([lbl, conf]) => (
                <div key={lbl} style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.3rem" }}>
                  <div style={{ flex: 1, height: "5px", background: "var(--bg-raised)", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${Math.round(conf * 100)}%`, height: "100%", background: "var(--accent)", transition: "width 0.4s" }} />
                  </div>
                  <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "#C8D4EA", whiteSpace: "nowrap" }}>
                    {lbl.replace(/_/g, " ")} {Math.round(conf * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Image panel */}
          <div style={{
            flex: 1,
            padding: "1.5rem",
            display: "flex", alignItems: "center", justifyContent: "center",
            minHeight: "320px",
            background: "var(--bg-base)",
          }}>
            {imgLoading && <div className="skeleton" style={{ width: "100%", height: "360px", borderRadius: "var(--radius)" }} />}
            {!imgLoading && imgBlobUrl && (
              <img
                src={imgBlobUrl}
                alt={`Classified document ${displayName(prediction)}`}
                style={{
                  maxWidth: "100%", maxHeight: "520px",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                  objectFit: "contain",
                  boxShadow: "0 10px 40px rgba(0,0,0,0.35)",
                }}
              />
            )}
            {!imgLoading && imgError && (
              <div style={{ textAlign: "center", color: "#C8D4EA", maxWidth: "320px" }}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" style={{ opacity: 0.4, display: "block", margin: "0 auto 0.75rem" }}>
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                  <path d="M3 9h18M9 21V9"/>
                </svg>
                <p style={{ fontSize: "14px", margin: 0, color: "#E8F0FF" }}>
                  {imgError}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Inline comment editor ─────────────────────────────────────────────────────

function CommentEditor({
  prediction, onSave, onCancel, isSaving,
}: {
  prediction: PredictionOut;
  onSave: (comment: string | null, color: string | null) => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  const [text, setText] = useState(prediction.comment ?? "");
  const [color, setColor] = useState(prediction.comment_color ?? "");

  return (
    <div style={{
      padding: "0.75rem",
      background: "var(--bg-raised)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius)",
      display: "flex", flexDirection: "column", gap: "0.6rem",
    }}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Add a note or review comment…"
        rows={2}
        style={{
          width: "100%", resize: "none",
          background: "var(--bg-surface)",
          color: "var(--text)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          padding: "0.55rem 0.75rem",
          fontSize: "14px",
          fontFamily: "var(--font-body)",
          outline: "none",
          boxSizing: "border-box",
        }}
      />
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
        <span style={{ fontSize: "13px", color: "#C8D4EA" }}>Color:</span>
        {COMMENT_COLORS.map((c) => (
          <button
            key={c.value}
            title={c.label}
            onClick={() => setColor(color === c.value ? "" : c.value)}
            style={{
              width: "18px", height: "18px",
              borderRadius: "50%",
              background: c.hex,
              border: color === c.value ? "2px solid #fff" : "2px solid transparent",
              cursor: "pointer",
              flexShrink: 0,
              transition: "border 0.12s",
            }}
          />
        ))}
        <div style={{ marginLeft: "auto", display: "flex", gap: "0.4rem" }}>
          <button className="btn btn-ghost btn-sm" onClick={onCancel} disabled={isSaving} style={{ fontSize: "12px" }}>
            Cancel
          </button>
          <button
            className="btn btn-sm"
            onClick={() => onSave(text.trim() || null, color || null)}
            disabled={isSaving}
            style={{ fontSize: "12px", background: "var(--accent)", color: "#06080F", fontWeight: "600" }}
          >
            {isSaving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Card color picker ────────────────────────────────────────────────────────

function CardColorPicker({
  prediction, onSave, onCancel, isSaving,
}: {
  prediction: PredictionOut;
  onSave: (color: string | null) => void;
  onCancel: () => void;
  isSaving: boolean;
}) {
  return (
    <div style={{
      padding: "0.6rem 1rem",
      background: "var(--bg-raised)",
      borderTop: "1px solid var(--border-subtle)",
      display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap",
    }}>
      <span style={{ fontSize: "13px", color: "#C8D4EA" }}>Card color:</span>
      {COMMENT_COLORS.map((c) => (
        <button
          key={c.value}
          title={c.label}
          disabled={isSaving}
          onClick={() => onSave(prediction.comment_color === c.value ? null : c.value)}
          style={{
            width: "22px", height: "22px",
            borderRadius: "50%",
            background: c.hex,
            border: prediction.comment_color === c.value ? "2px solid #fff" : "2px solid transparent",
            cursor: "pointer",
            transition: "border 0.12s, transform 0.1s",
          }}
          onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.transform = "scale(1.2)"}
          onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.transform = "scale(1)"}
        />
      ))}
      {prediction.comment_color && (
        <button
          title="Clear color"
          disabled={isSaving}
          onClick={() => onSave(null)}
          style={{
            fontSize: "12px", color: "#C8D4EA", background: "none",
            border: "1px solid var(--border-subtle)", borderRadius: "4px",
            padding: "0.15rem 0.5rem", cursor: "pointer",
          }}
        >
          Clear
        </button>
      )}
      <button className="btn btn-ghost btn-sm" onClick={onCancel} style={{ marginLeft: "auto", fontSize: "12px" }}>
        Done
      </button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DocumentsPage() {
  const role = getRole();
  const queryClient = useQueryClient();
  const canEdit = role === "admin" || role === "reviewer";

  const [viewMode, setViewMode] = useState<"grid" | "card">("grid");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [labelFilter, setLabelFilter] = useState<string>("");
  const [colorFilter, setColorFilter] = useState<string>("");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  const [viewingPred, setViewingPred] = useState<PredictionOut | null>(null);
  const [editingLabel, setEditingLabel] = useState<string | null>(null);
  const [editingComment, setEditingComment] = useState<string | null>(null);
  const [editingColor, setEditingColor] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState<string>("");

  const queryKey = ["predictions", "paginated", page, pageSize, labelFilter, colorFilter];

  const { data: predictions, isLoading, isError } = useQuery<PredictionOut[]>({
    queryKey,
    queryFn: async () => {
      const params: Record<string, string | number> = { page, limit: pageSize };
      if (labelFilter) params.label = labelFilter;
      if (colorFilter) params.color = colorFilter;
      const res = await client.get<PredictionOut[]>("/predictions", { params });
      return res.data;
    },
    staleTime: 15_000,
    placeholderData: (prev) => prev,
  });

  // Fetch all predictions (no pagination) when in Card view for category counts + filtering.
  const { data: allPredictions } = useQuery<PredictionOut[]>({
    queryKey: ["predictions", "all"],
    queryFn: async () => {
      const res = await client.get<PredictionOut[]>("/predictions", { params: { page: 1, limit: 500 } });
      return res.data;
    },
    enabled: viewMode === "card",
    staleTime: 15_000,
  });

  const relabelMutation = useMutation({
    mutationFn: async ({ pid, label }: { pid: string; label: string }) => {
      const res = await client.patch<PredictionOut>(`/predictions/${pid}/label`, { new_label: label });
      return res.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<PredictionOut[]>(queryKey, (old) =>
        old?.map((p) => (p.id === updated.id ? updated : p)) ?? []
      );
      void queryClient.invalidateQueries({ queryKey: ["predictions"] });
      setEditingLabel(null);
      setToast({ msg: `Label updated to "${updated.label}".`, type: "success" });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      const detail = err?.response?.data?.detail ?? "Failed to update label.";
      setToast({ msg: detail, type: "error" });
      setEditingLabel(null);
    },
  });

  const commentMutation = useMutation({
    mutationFn: async ({ pid, comment, color }: { pid: string; comment: string | null; color: string | null }) => {
      const res = await client.patch<PredictionOut>(`/predictions/${pid}/comment`, { comment, comment_color: color });
      return res.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<PredictionOut[]>(queryKey, (old) =>
        old?.map((p) => (p.id === updated.id ? updated : p)) ?? []
      );
      setEditingComment(null);
      setEditingColor(null);
      setToast({ msg: "Saved.", type: "success" });
    },
    onError: () => setToast({ msg: "Failed to save.", type: "error" }),
  });

  const renameMutation = useMutation({
    mutationFn: async ({ pid, name }: { pid: string; name: string | null }) => {
      const res = await client.patch<PredictionOut>(`/predictions/${pid}/name`, { document_name: name });
      return res.data;
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<PredictionOut[]>(queryKey, (old) =>
        old?.map((p) => (p.id === updated.id ? updated : p)) ?? []
      );
      setEditingName(null);
      setToast({ msg: "Document renamed.", type: "success" });
    },
    onError: () => setToast({ msg: "Failed to rename document.", type: "error" }),
  });

  function applyCardColor(pred: PredictionOut, newColor: string | null) {
    commentMutation.mutate({ pid: pred.id, comment: pred.comment ?? null, color: newColor });
  }

  function commitRename(pred: PredictionOut) {
    const trimmed = nameDraft.trim();
    const newName = trimmed === "" ? null : trimmed;
    const currentName = pred.document_name ?? null;
    if (newName === currentName) {
      setEditingName(null);
      return;
    }
    renameMutation.mutate({ pid: pred.id, name: newName });
  }

  const hasNext = (predictions?.length ?? 0) >= pageSize;
  const hasPrev = page > 1;

  const cardBorderColor = (pred: PredictionOut) =>
    pred.comment_color
      ? COMMENT_COLORS.find((c) => c.value === pred.comment_color)?.hex ?? "transparent"
      : "transparent";

  // Bigger, brighter action button base style
  const actionBtnBase = {
    background: "var(--bg-raised)",
    border: "1px solid var(--border)",
    cursor: "pointer",
    padding: "0.45rem",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "background 0.12s, border-color 0.12s, color 0.12s",
    width: "32px",
    height: "32px",
  };

  const viewToggle = (
    <div style={{
      display: "flex",
      gap: "0.4rem",
      background: "var(--bg-raised)",
      padding: "0.35rem",
      borderRadius: "8px",
      border: "1px solid var(--border)",
    }}>
      {(["grid", "card"] as const).map((mode) => (
        <button
          key={mode}
          onClick={() => {
            setViewMode(mode);
            setSelectedCategory(null);
          }}
          style={{
            padding: "0.35rem 0.85rem",
            background: viewMode === mode ? "var(--accent)" : "transparent",
            color: viewMode === mode ? "#06080F" : "#E8F0FF",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "13px",
            fontWeight: viewMode === mode ? 600 : 500,
            fontFamily: "var(--font-display)",
            transition: "all 0.15s",
          }}
        >
          {mode === "grid" ? "Grid" : "Categories"}
        </button>
      ))}
    </div>
  );

  return (
    <Layout
      title="Documents"
      subtitle="Classified documents — click labels, names, or comments to edit"
      actions={viewToggle}
    >
      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
      {viewingPred && <DocViewModal prediction={viewingPred} onClose={() => setViewingPred(null)} />}

      {/* Filter bar — Grid view only */}
      {viewMode === "grid" && (
        <div style={{
          display: "flex", alignItems: "center", gap: "0.75rem",
          marginBottom: "1.25rem", flexWrap: "wrap",
        }}>
          <select
            className="select"
            value={labelFilter}
            onChange={(e) => { setLabelFilter(e.target.value); setPage(1); }}
            style={{ minWidth: "160px" }}
          >
            <option value="">All labels</option>
            {PREDICTION_LABELS.map((l) => (
              <option key={l} value={l}>{l.replace(/_/g, " ")}</option>
            ))}
          </select>

          <select
            className="select"
            value={colorFilter}
            onChange={(e) => { setColorFilter(e.target.value); setPage(1); }}
            style={{ minWidth: "140px" }}
          >
            <option value="">All colors</option>
            {COMMENT_COLORS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>

          {(labelFilter || colorFilter) && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => { setLabelFilter(""); setColorFilter(""); setPage(1); }}
              style={{ fontSize: "13px" }}
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {isError && (
        <div style={{
          padding: "1rem",
          background: "rgba(239,68,68,0.06)",
          border: "1px solid rgba(239,68,68,0.2)",
          borderRadius: "var(--radius)",
          color: "var(--danger)", fontSize: "15px",
          marginBottom: "1rem",
        }}>
          Failed to load documents.
        </div>
      )}

      {viewMode === "grid" && (
        <>
          {/* Column header — larger, brighter, properly aligned */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "1.5fr 140px 110px 100px 120px 140px",
            gap: "0.75rem",
            padding: "0.7rem 1rem 0.7rem 1.25rem",
            fontSize: "13px",
            fontFamily: "var(--font-display)",
            color: "#E8F0FF",
            fontWeight: 600,
            letterSpacing: "0.04em",
            borderBottom: "1px solid var(--border)",
            marginBottom: "0.5rem",
          }}>
            <span>Document</span>
            <span>Label</span>
            <span>Confidence</span>
            <span>Latency</span>
            <span>Date</span>
            <span style={{ textAlign: "right" }}>Actions</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {isLoading && Array.from({ length: pageSize > 6 ? 6 : pageSize }).map((_, i) => (
              <div key={i} className="card" style={{
                padding: "0.85rem 1rem",
                display: "grid",
                gridTemplateColumns: "1.5fr 140px 110px 100px 120px 140px",
                gap: "0.75rem", alignItems: "center",
              }}>
                {Array.from({ length: 6 }).map((_, j) => (
                  <div key={j} className="skeleton" style={{ height: "14px", width: j === 0 ? "70%" : "60%" }} />
                ))}
              </div>
            ))}

        {!isLoading && predictions?.length === 0 && (
          <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            No documents found
            {labelFilter && ` with label "${labelFilter.replace(/_/g, " ")}"`}
            {colorFilter && ` with ${colorFilter} color`}.
          </div>
        )}

        {predictions?.map((pred, idx) => {
          const borderColor = cardBorderColor(pred);
          const isEditingName = editingName === pred.id;
          return (
            <div
              key={pred.id}
              className="card animate-fade-up"
              style={{
                animationDelay: `${idx * 25}ms`,
                overflow: "visible",
                borderLeft: `3px solid ${borderColor}`,
                transition: "border-color 0.2s",
              }}
            >
              {/* Main row */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "1.5fr 140px 110px 100px 120px 140px",
                gap: "0.75rem", alignItems: "center",
                padding: "0.85rem 1rem",
              }}>
                {/* Document name — editable */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 0 }}>
                  <ColorDot color={pred.comment_color} size={9} />
                  {isEditingName ? (
                    <input
                      autoFocus
                      value={nameDraft}
                      onChange={(e) => setNameDraft(e.target.value)}
                      onBlur={() => commitRename(pred)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") { e.currentTarget.blur(); }
                        if (e.key === "Escape") { setEditingName(null); }
                      }}
                      placeholder={fallbackDocName(pred)}
                      disabled={renameMutation.isPending}
                      style={{
                        background: "var(--bg-surface)",
                        color: "#E8F0FF",
                        border: "1px solid var(--accent)",
                        borderRadius: "4px",
                        padding: "0.25rem 0.5rem",
                        fontSize: "14px",
                        fontFamily: "var(--font-mono)",
                        width: "100%",
                        outline: "none",
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        display: "flex", alignItems: "center", gap: "0.35rem",
                        cursor: canEdit ? "pointer" : "default",
                        minWidth: 0,
                      }}
                      onClick={() => {
                        if (!canEdit) return;
                        setNameDraft(pred.document_name ?? "");
                        setEditingName(pred.id);
                      }}
                      title={canEdit ? "Click to rename" : undefined}
                    >
                      <span style={{
                        fontSize: "14px",
                        color: pred.document_name ? "#E8F0FF" : "var(--text)",
                        fontFamily: pred.document_name ? "var(--font-body)" : "var(--font-mono)",
                        fontWeight: pred.document_name ? 500 : 400,
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}>
                        {displayName(pred)}
                      </span>
                      {canEdit && (
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#7A8DAE" strokeWidth="2.5" style={{ flexShrink: 0 }}>
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                      )}
                    </div>
                  )}
                </div>

                {/* Label */}
                <div>
                  {canEdit && editingLabel === pred.id ? (
                    <select
                      autoFocus
                      className="select"
                      defaultValue={pred.label}
                      disabled={relabelMutation.isPending}
                      style={{ fontSize: "13px", padding: "0.25rem 0.5rem" }}
                      onChange={(e) => relabelMutation.mutate({ pid: pred.id, label: e.target.value })}
                      onBlur={() => setEditingLabel(null)}
                    >
                      {PREDICTION_LABELS.map((l) => (
                        <option key={l} value={l}>{l.replace(/_/g, " ")}</option>
                      ))}
                    </select>
                  ) : (
                    <div
                      style={{ display: "flex", alignItems: "center", gap: "0.4rem", cursor: canEdit ? "pointer" : "default" }}
                      onClick={() => canEdit && setEditingLabel(pred.id)}
                      title={canEdit ? "Click to relabel" : undefined}
                    >
                      <LabelBadge label={pred.label} />
                      {canEdit && (
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#7A8DAE" strokeWidth="2.5" style={{ flexShrink: 0 }}>
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                      )}
                    </div>
                  )}
                </div>

                <ConfidencePill value={pred.top1_confidence} />
                <LatencyPill ms={pred.latency_ms} />

                <span style={{ fontSize: "13px", color: "#C8D4EA", whiteSpace: "nowrap" }}>
                  {formatDate(pred.created_at)}
                </span>

                {/* Actions — bigger, brighter, with hover */}
                <div style={{ display: "flex", gap: "0.35rem", alignItems: "center", justifyContent: "flex-end" }}>
                  <button
                    title="View document"
                    onClick={() => setViewingPred(pred)}
                    style={{ ...actionBtnBase, color: "#E8F0FF" }}
                    onMouseEnter={(e) => {
                      const el = e.currentTarget as HTMLElement;
                      el.style.background = "var(--accent-glow)";
                      el.style.borderColor = "var(--accent)";
                      el.style.color = "var(--accent)";
                    }}
                    onMouseLeave={(e) => {
                      const el = e.currentTarget as HTMLElement;
                      el.style.background = "var(--bg-raised)";
                      el.style.borderColor = "var(--border)";
                      el.style.color = "#E8F0FF";
                    }}
                  >
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  </button>

                  {canEdit && (
                    <button
                      title={pred.comment ? "Edit note" : "Add note"}
                      onClick={() => {
                        setEditingComment(editingComment === pred.id ? null : pred.id);
                        setEditingColor(null);
                      }}
                      style={{
                        ...actionBtnBase,
                        color: pred.comment ? "var(--accent-warm)" : "#E8F0FF",
                        borderColor: pred.comment ? "rgba(245,158,11,0.4)" : "var(--border)",
                      }}
                      onMouseEnter={(e) => {
                        const el = e.currentTarget as HTMLElement;
                        el.style.background = "rgba(245,158,11,0.1)";
                        el.style.borderColor = "var(--accent-warm)";
                        el.style.color = "var(--accent-warm)";
                      }}
                      onMouseLeave={(e) => {
                        const el = e.currentTarget as HTMLElement;
                        el.style.background = "var(--bg-raised)";
                        el.style.borderColor = pred.comment ? "rgba(245,158,11,0.4)" : "var(--border)";
                        el.style.color = pred.comment ? "var(--accent-warm)" : "#E8F0FF";
                      }}
                    >
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                      </svg>
                    </button>
                  )}

                  {canEdit && (
                    <button
                      title="Set card color"
                      onClick={() => {
                        setEditingColor(editingColor === pred.id ? null : pred.id);
                        setEditingComment(null);
                      }}
                      style={{
                        ...actionBtnBase,
                        color: pred.comment_color ? COMMENT_COLORS.find(c => c.value === pred.comment_color)?.hex ?? "#E8F0FF" : "#E8F0FF",
                        borderColor: pred.comment_color ? `${COMMENT_COLORS.find(c => c.value === pred.comment_color)?.hex}60` : "var(--border)",
                      }}
                      onMouseEnter={(e) => {
                        const el = e.currentTarget as HTMLElement;
                        el.style.background = "var(--accent-glow)";
                        el.style.borderColor = "var(--accent)";
                      }}
                      onMouseLeave={(e) => {
                        const el = e.currentTarget as HTMLElement;
                        el.style.background = "var(--bg-raised)";
                        el.style.borderColor = pred.comment_color ? `${COMMENT_COLORS.find(c => c.value === pred.comment_color)?.hex}60` : "var(--border)";
                      }}
                    >
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.1">
                        <circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/>
                        <circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>
                        <circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>
                        <circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>
                        <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>
                      </svg>
                    </button>
                  )}
                </div>
              </div>

              {canEdit && editingColor === pred.id && (
                <CardColorPicker
                  prediction={pred}
                  onSave={(color) => applyCardColor(pred, color)}
                  onCancel={() => setEditingColor(null)}
                  isSaving={commentMutation.isPending}
                />
              )}

              {pred.comment && editingComment !== pred.id && (
                <div style={{
                  margin: "0 1rem 0.75rem",
                  padding: "0.5rem 0.75rem",
                  background: "var(--bg-raised)",
                  borderLeft: `3px solid ${COMMENT_COLORS.find((c) => c.value === pred.comment_color)?.hex ?? "var(--border)"}`,
                  borderRadius: "var(--radius)",
                  display: "flex", alignItems: "flex-start", gap: "0.5rem",
                }}>
                  <ColorDot color={pred.comment_color} />
                  <span style={{ fontSize: "14px", color: "#E8F0FF", lineHeight: 1.5 }}>
                    {pred.comment}
                  </span>
                </div>
              )}

              {canEdit && editingComment === pred.id && (
                <div style={{ margin: "0 1rem 0.75rem" }}>
                  <CommentEditor
                    prediction={pred}
                    onSave={(comment, color) => commentMutation.mutate({ pid: pred.id, comment, color })}
                    onCancel={() => setEditingComment(null)}
                    isSaving={commentMutation.isPending}
                  />
                </div>
              )}
            </div>
          );
        })}
          </div>

          {/* Bottom pagination — with rows-per-page selector */}
          {(predictions?.length ?? 0) > 0 && (
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "1.25rem",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <label style={{ fontSize: "13px", color: "#C8D4EA", whiteSpace: "nowrap" }}>Rows per page:</label>
            <input
              type="number"
              min={1}
              max={100}
              value={pageSize}
              onChange={(e) => {
                const v = Math.max(1, Math.min(100, Number(e.target.value) || 10));
                setPageSize(v);
                setPage(1);
              }}
              style={{
                width: "60px",
                background: "var(--bg-surface)",
                color: "#E8F0FF",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                padding: "0.3rem 0.5rem",
                fontSize: "14px",
                fontFamily: "var(--font-mono)",
                textAlign: "center",
                outline: "none",
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setPage((p) => p - 1)}
              disabled={!hasPrev}
            >
              ← Prev
            </button>
            <span style={{
              fontSize: "14px",
              fontFamily: "var(--font-mono)",
              color: "#E8F0FF",
              minWidth: "64px",
              textAlign: "center",
              fontWeight: 500,
            }}>
              Page {page}
            </span>
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext}
            >
              Next →
            </button>
          </div>
        </div>
      )}
        </>
      )}

      {/* Card View */}
      {viewMode === "card" && (
        <>
          {!selectedCategory ? (
            // Category browser — sorted by count descending
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: "1.25rem",
              marginBottom: "2rem",
            }}>
              {(() => {
                const iconMap: Record<string, string> = {
                  letter: "📄", form: "📋", email: "✉️", handwritten: "✍️",
                  advertisement: "📢", scientific_report: "🔬", scientific_publication: "📚",
                  specification: "📐", file_folder: "📁", news_article: "📰",
                  budget: "💰", invoice: "🧾", presentation: "🎯",
                  questionnaire: "❓", resume: "👤", memo: "📝",
                };

                const categoriesWithCounts = PREDICTION_LABELS.map((label) => ({
                  label,
                  count: allPredictions?.filter((p) => p.label === label).length ?? 0,
                })).sort((a, b) => b.count - a.count);

                return categoriesWithCounts.map(({ label, count }) => {
                  const labelDisplay = label.replace(/_/g, " ");
                  const isEmpty = count === 0;
                  return (
                    <button
                      key={label}
                      disabled={isEmpty}
                      onClick={() => {
                        setSelectedCategory(label);
                        setPage(1);
                      }}
                      style={{
                        background: "var(--bg-raised)",
                        border: "1px solid var(--border)",
                        borderRadius: "14px",
                        padding: "2rem 1.25rem",
                        cursor: isEmpty ? "not-allowed" : "pointer",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "1rem",
                        minHeight: "200px",
                        transition: "all 0.2s",
                        opacity: isEmpty ? 0.4 : 1,
                      }}
                      onMouseEnter={(e) => {
                        if (isEmpty) return;
                        (e.currentTarget as HTMLElement).style.background = "var(--accent-glow)";
                        (e.currentTarget as HTMLElement).style.borderColor = "var(--accent)";
                        (e.currentTarget as HTMLElement).style.transform = "translateY(-4px)";
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.background = "var(--bg-raised)";
                        (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                        (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                      }}
                    >
                      <div style={{
                        fontSize: "64px",
                        lineHeight: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: "92px",
                        height: "92px",
                        background: "var(--accent-glow)",
                        borderRadius: "14px",
                      }}>
                        {iconMap[label] || "📄"}
                      </div>
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: "15px", fontWeight: 600, color: "#E8F0FF", marginBottom: "0.4rem", fontFamily: "var(--font-display)", textTransform: "capitalize" }}>
                          {labelDisplay}
                        </div>
                        <div style={{
                          fontSize: "13px",
                          color: count > 0 ? "var(--accent)" : "#7A8DAE",
                          fontFamily: "var(--font-mono)",
                          fontWeight: count > 0 ? 600 : 400,
                        }}>
                          {count} {count === 1 ? "document" : "documents"}
                        </div>
                      </div>
                    </button>
                  );
                });
              })()}
            </div>
          ) : (
            // Document cards in selected category
            <div>
              <button
                onClick={() => setSelectedCategory(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--accent)",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontFamily: "var(--font-display)",
                  marginBottom: "1.5rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                ← Back to categories
              </button>

              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
                gap: "1.75rem",
              }}>
                {allPredictions?.filter((p) => p.label === selectedCategory).map((pred) => (
                  <div
                    key={pred.id}
                    className="card animate-fade-up"
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      borderLeft: `4px solid ${COMMENT_COLORS.find((c) => c.value === pred.comment_color)?.hex ?? "var(--border)"}`,
                      overflow: "hidden",
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.transform = "translateY(-6px)";
                      (e.currentTarget as HTMLElement).style.boxShadow = "0 20px 50px rgba(0,0,0,0.5)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                      (e.currentTarget as HTMLElement).style.boxShadow = "none";
                    }}
                  >
                    {/* Preview area — auto-loaded image */}
                    <div
                      onClick={() => setViewingPred(pred)}
                      style={{
                        height: "320px",
                        background: "var(--bg-base)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "pointer",
                        position: "relative",
                        overflow: "hidden",
                      }}
                      title="Click to open full view"
                    >
                      <DocPreviewImage prediction={pred} />
                    </div>

                    {/* Info section */}
                    <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.9rem" }}>
                      {/* Document name */}
                      <div>
                        <div style={{ fontSize: "11px", color: "#7A8DAE", fontFamily: "var(--font-mono)", marginBottom: "0.3rem", textTransform: "uppercase" }}>
                          Document
                        </div>
                        {editingName === pred.id ? (
                          <input
                            autoFocus
                            value={nameDraft}
                            onChange={(e) => setNameDraft(e.target.value)}
                            onBlur={() => commitRename(pred)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") e.currentTarget.blur();
                              if (e.key === "Escape") setEditingName(null);
                            }}
                            placeholder={fallbackDocName(pred)}
                            style={{
                              width: "100%",
                              background: "var(--bg-surface)",
                              color: "#E8F0FF",
                              border: "1px solid var(--accent)",
                              borderRadius: "4px",
                              padding: "0.4rem 0.6rem",
                              fontSize: "14px",
                              outline: "none",
                            }}
                          />
                        ) : (
                          <div
                            onClick={() => canEdit && setEditingName(pred.id)}
                            style={{
                              fontSize: "14px",
                              fontWeight: 500,
                              color: "#E8F0FF",
                              cursor: canEdit ? "pointer" : "default",
                            }}
                          >
                            {displayName(pred)}
                          </div>
                        )}
                      </div>

                      {/* Label + Confidence + Latency */}
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                        <div>
                          <div style={{ fontSize: "11px", color: "#7A8DAE", fontFamily: "var(--font-mono)", marginBottom: "0.3rem", textTransform: "uppercase" }}>
                            Label
                          </div>
                          {editingLabel === pred.id && canEdit ? (
                            <select
                              autoFocus
                              className="select"
                              defaultValue={pred.label}
                              disabled={relabelMutation.isPending}
                              style={{ fontSize: "12px", padding: "0.3rem" }}
                              onChange={(e) => relabelMutation.mutate({ pid: pred.id, label: e.target.value })}
                              onBlur={() => setEditingLabel(null)}
                            >
                              {PREDICTION_LABELS.map((l) => (
                                <option key={l} value={l}>{l.replace(/_/g, " ")}</option>
                              ))}
                            </select>
                          ) : (
                            <div onClick={() => canEdit && setEditingLabel(pred.id)} style={{ cursor: canEdit ? "pointer" : "default" }}>
                              <LabelBadge label={pred.label} />
                            </div>
                          )}
                        </div>
                        <div>
                          <div style={{ fontSize: "11px", color: "#7A8DAE", fontFamily: "var(--font-mono)", marginBottom: "0.3rem", textTransform: "uppercase" }}>
                            Confidence
                          </div>
                          <ConfidencePill value={pred.top1_confidence} />
                        </div>
                      </div>

                      {/* Latency */}
                      <div>
                        <div style={{ fontSize: "11px", color: "#7A8DAE", fontFamily: "var(--font-mono)", marginBottom: "0.3rem", textTransform: "uppercase" }}>
                          Latency
                        </div>
                        <LatencyPill ms={pred.latency_ms} />
                      </div>

                      {/* Comment preview */}
                      {pred.comment && (
                        <div style={{
                          padding: "0.5rem 0.75rem",
                          background: "var(--bg-raised)",
                          borderLeft: `2px solid ${COMMENT_COLORS.find((c) => c.value === pred.comment_color)?.hex ?? "var(--border)"}`,
                          borderRadius: "4px",
                        }}>
                          <div style={{ fontSize: "12px", color: "#E8F0FF", lineHeight: 1.4 }}>
                            {pred.comment.substring(0, 60)}
                            {pred.comment.length > 60 ? "..." : ""}
                          </div>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div style={{
                        display: "flex",
                        gap: "0.4rem",
                        marginTop: "0.5rem",
                        flexWrap: "wrap",
                      }}>
                        <button
                          title="View full document"
                          onClick={() => setViewingPred(pred)}
                          style={{
                            flex: 1,
                            padding: "0.4rem 0.6rem",
                            background: "var(--accent)",
                            color: "#06080F",
                            border: "none",
                            borderRadius: "6px",
                            cursor: "pointer",
                            fontSize: "12px",
                            fontWeight: 600,
                            fontFamily: "var(--font-display)",
                            transition: "all 0.15s",
                          }}
                          onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.opacity = "0.85"}
                          onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.opacity = "1"}
                        >
                          View
                        </button>

                        {canEdit && (
                          <>
                            <button
                              title="Edit label"
                              onClick={() => setEditingLabel(pred.id)}
                              style={{
                                padding: "0.4rem 0.6rem",
                                background: "var(--bg-raised)",
                                border: "1px solid var(--border)",
                                color: "#E8F0FF",
                                borderRadius: "6px",
                                cursor: "pointer",
                                fontSize: "12px",
                                fontWeight: 500,
                                fontFamily: "var(--font-display)",
                              }}
                            >
                              Label
                            </button>
                            <button
                              title="Add comment"
                              onClick={() => setEditingComment(pred.id)}
                              style={{
                                padding: "0.4rem 0.6rem",
                                background: "var(--bg-raised)",
                                border: "1px solid var(--border)",
                                color: "#E8F0FF",
                                borderRadius: "6px",
                                cursor: "pointer",
                                fontSize: "12px",
                                fontWeight: 500,
                                fontFamily: "var(--font-display)",
                              }}
                            >
                              Note
                            </button>
                            <button
                              title="Set color"
                              onClick={() => setEditingColor(pred.id)}
                              style={{
                                padding: "0.4rem 0.6rem",
                                background: "var(--bg-raised)",
                                border: "1px solid var(--border)",
                                color: "#E8F0FF",
                                borderRadius: "6px",
                                cursor: "pointer",
                                fontSize: "12px",
                                fontWeight: 500,
                                fontFamily: "var(--font-display)",
                              }}
                            >
                              Color
                            </button>
                          </>
                        )}
                      </div>

                      {/* Comment editor */}
                      {editingComment === pred.id && canEdit && (
                        <div style={{ marginTop: "0.5rem" }}>
                          <CommentEditor
                            prediction={pred}
                            onSave={(comment, color) => commentMutation.mutate({ pid: pred.id, comment, color })}
                            onCancel={() => setEditingComment(null)}
                            isSaving={commentMutation.isPending}
                          />
                        </div>
                      )}

                      {/* Color picker */}
                      {editingColor === pred.id && canEdit && (
                        <div style={{ marginTop: "0.5rem" }}>
                          <CardColorPicker
                            prediction={pred}
                            onSave={(color) => applyCardColor(pred, color)}
                            onCancel={() => setEditingColor(null)}
                            isSaving={commentMutation.isPending}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}
