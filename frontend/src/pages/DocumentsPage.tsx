import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Layout } from "../components/Layout";
import { LabelBadge } from "../components/LabelBadge";
import { Toast } from "../components/Toast";
import client from "../api/client";
import { getRole } from "../hooks/useAuth";
import type { PredictionOut } from "../api/types";
import { PREDICTION_LABELS, COMMENT_COLORS } from "../api/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function docName(pred: PredictionOut): string {
  return `DOC-${pred.document_id.slice(0, 8).toUpperCase()}`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
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
      padding: "0.15rem 0.5rem",
      borderRadius: "4px",
      fontSize: "13px",
      fontFamily: "var(--font-mono)",
      color,
      background: `${color}18`,
      border: `1px solid ${color}28`,
    }}>
      {pct}%
    </span>
  );
}

// ── Latency pill ─────────────────────────────────────────────────────────────

function LatencyPill({ ms }: { ms: number | null }) {
  if (ms === null || ms === undefined) {
    return <span style={{ color: "var(--text-dim)", fontSize: "13px" }}>—</span>;
  }
  const color = ms < 500 ? "var(--success)" : ms < 1000 ? "var(--accent)" : "var(--warning)";
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color }}>
      {ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`}
    </span>
  );
}

// ── Document viewer modal ─────────────────────────────────────────────────────

function DocViewModal({ prediction, onClose }: { prediction: PredictionOut; onClose: () => void }) {
  const [imgError, setImgError] = useState(false);

  const { data, isLoading } = useQuery<{ overlay_url: string | null; document_url: string | null }>({
    queryKey: ["doc-url", prediction.id],
    queryFn: async () => {
      const res = await client.get(`/predictions/${prediction.id}/document-url`);
      return res.data;
    },
    staleTime: 300_000,
  });

  const imageUrl = !imgError && data?.overlay_url ? data.overlay_url : null;
  const hasImage = !!imageUrl;

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
          width: "100%", maxWidth: "860px",
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
            <h3 style={{ fontSize: "16px", margin: 0, fontFamily: "var(--font-display)", color: "#E8F0FF" }}>
              {docName(prediction)}
            </h3>
            <LabelBadge label={prediction.label} />
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: "0.25rem" }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Body: metadata left + image right */}
        <div style={{ display: "flex", overflow: "auto", flex: 1 }}>
          {/* Metadata panel */}
          <div style={{
            flex: "0 0 220px",
            borderRight: "1px solid var(--border-subtle)",
            padding: "1.25rem",
            display: "flex", flexDirection: "column", gap: "1rem",
          }}>
            {[
              { label: "Confidence", value: <ConfidencePill value={prediction.top1_confidence} /> },
              { label: "Latency", value: <LatencyPill ms={prediction.latency_ms} /> },
              { label: "Classified", value: <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>{formatDate(prediction.created_at)}</span> },
              { label: "Batch", value: <code style={{ fontSize: "12px", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>{prediction.batch_id.slice(0, 8)}…</code> },
            ].map(({ label, value }) => (
              <div key={label}>
                <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.3rem" }}>
                  {label}
                </div>
                {value}
              </div>
            ))}
            {prediction.comment && (
              <div>
                <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.4rem" }}>
                  Note
                </div>
                <div style={{
                  padding: "0.5rem 0.6rem",
                  background: "var(--bg-raised)",
                  borderLeft: `3px solid ${COMMENT_COLORS.find(c => c.value === prediction.comment_color)?.hex ?? "var(--border)"}`,
                  borderRadius: "var(--radius)",
                  fontSize: "13px",
                  color: "var(--text)",
                  lineHeight: 1.5,
                }}>
                  {prediction.comment}
                </div>
              </div>
            )}
            {/* Top-5 breakdown */}
            <div>
              <div style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.5rem" }}>
                Top-5
              </div>
              {prediction.top5.slice(0, 5).map(([lbl, conf]) => (
                <div key={lbl} style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.3rem" }}>
                  <div style={{ flex: 1, height: "4px", background: "var(--bg-raised)", borderRadius: "2px", overflow: "hidden" }}>
                    <div style={{ width: `${Math.round(conf * 100)}%`, height: "100%", background: "var(--accent)", transition: "width 0.4s" }} />
                  </div>
                  <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
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
            minHeight: "300px",
            background: "var(--bg-base)",
          }}>
            {isLoading && (
              <div className="skeleton" style={{ width: "100%", height: "320px", borderRadius: "var(--radius)" }} />
            )}
            {!isLoading && hasImage && (
              <img
                src={imageUrl!}
                alt={`Classified document ${docName(prediction)}`}
                onError={() => setImgError(true)}
                style={{
                  maxWidth: "100%", maxHeight: "480px",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                  objectFit: "contain",
                }}
              />
            )}
            {!isLoading && !hasImage && (
              <div style={{ textAlign: "center", color: "var(--text-muted)" }}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" style={{ opacity: 0.3, display: "block", margin: "0 auto 0.75rem" }}>
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                  <path d="M3 9h18M9 21V9"/>
                </svg>
                <p style={{ fontSize: "14px", margin: "0 0 0.4rem" }}>
                  {data?.overlay_url === null ? "No overlay generated yet" : "Image preview unavailable"}
                </p>
                <p style={{ fontSize: "12px", margin: 0, maxWidth: "260px" }}>
                  {data?.overlay_url === null
                    ? "This document may still be queued for classification."
                    : "The overlay image could not be loaded. This is common in local dev mode when MinIO uses an internal hostname."}
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
  prediction,
  onSave,
  onCancel,
  isSaving,
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
          padding: "0.5rem 0.75rem",
          fontSize: "14px",
          fontFamily: "var(--font-body)",
          outline: "none",
          boxSizing: "border-box",
        }}
      />
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
        <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Color:</span>
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

// ── Inline card color picker ──────────────────────────────────────────────────

function CardColorPicker({
  prediction,
  onSave,
  onCancel,
  isSaving,
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
      <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Card color:</span>
      {COMMENT_COLORS.map((c) => (
        <button
          key={c.value}
          title={c.label}
          disabled={isSaving}
          onClick={() => onSave(prediction.comment_color === c.value ? null : c.value)}
          style={{
            width: "20px", height: "20px",
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
            fontSize: "12px", color: "var(--text-dim)", background: "none",
            border: "1px solid var(--border-subtle)", borderRadius: "4px",
            padding: "0.1rem 0.4rem", cursor: "pointer",
          }}
        >
          Clear
        </button>
      )}
      <button
        className="btn btn-ghost btn-sm"
        onClick={onCancel}
        style={{ marginLeft: "auto", fontSize: "12px" }}
      >
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

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [labelFilter, setLabelFilter] = useState<string>("");
  const [colorFilter, setColorFilter] = useState<string>("");
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  const [viewingPred, setViewingPred] = useState<PredictionOut | null>(null);
  const [editingLabel, setEditingLabel] = useState<string | null>(null);
  const [editingComment, setEditingComment] = useState<string | null>(null);
  const [editingColor, setEditingColor] = useState<string | null>(null);

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
      const res = await client.patch<PredictionOut>(`/predictions/${pid}/comment`, {
        comment,
        comment_color: color,
      });
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
    onError: () => {
      setToast({ msg: "Failed to save.", type: "error" });
    },
  });

  function applyCardColor(pred: PredictionOut, newColor: string | null) {
    commentMutation.mutate({ pid: pred.id, comment: pred.comment ?? null, color: newColor });
  }

  const hasNext = (predictions?.length ?? 0) >= pageSize;
  const hasPrev = page > 1;

  const cardBorderColor = (pred: PredictionOut) =>
    pred.comment_color
      ? COMMENT_COLORS.find((c) => c.value === pred.comment_color)?.hex ?? "transparent"
      : "transparent";

  return (
    <Layout
      title="Documents"
      subtitle="Classified documents — click labels to relabel, eye to view"
    >
      {toast && <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />}
      {viewingPred && <DocViewModal prediction={viewingPred} onClose={() => setViewingPred(null)} />}

      {/* Filter bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: "0.75rem",
        marginBottom: "1.25rem", flexWrap: "wrap",
      }}>
        {/* Label filter */}
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

        {/* Color filter */}
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

        {/* Page size */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <label style={{ fontSize: "13px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>Per page:</label>
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
              width: "54px",
              background: "var(--bg-surface)",
              color: "var(--text)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              padding: "0.25rem 0.4rem",
              fontSize: "13px",
              fontFamily: "var(--font-mono)",
              textAlign: "center",
              outline: "none",
            }}
          />
        </div>
      </div>

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

      {/* Column header */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 150px 100px 90px 140px auto",
        gap: "0.75rem",
        padding: "0.5rem 1rem 0.5rem 1.25rem",
        fontSize: "11px",
        fontFamily: "var(--font-mono)",
        color: "var(--text-dim)",
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        borderBottom: "1px solid var(--border-subtle)",
        marginBottom: "0.25rem",
      }}>
        <span>Document</span>
        <span>Label</span>
        <span>Confidence</span>
        <span>Latency</span>
        <span>Date</span>
        <span />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
        {/* Skeleton rows */}
        {isLoading && Array.from({ length: pageSize > 6 ? 6 : pageSize }).map((_, i) => (
          <div key={i} className="card" style={{
            padding: "0.75rem 1rem",
            display: "grid",
            gridTemplateColumns: "1fr 150px 100px 90px 140px auto",
            gap: "0.75rem", alignItems: "center",
          }}>
            {Array.from({ length: 6 }).map((_, j) => (
              <div key={j} className="skeleton" style={{ height: "14px", width: j === 0 ? "70%" : "60%" }} />
            ))}
          </div>
        ))}

        {/* Empty state */}
        {!isLoading && predictions?.length === 0 && (
          <div className="card" style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            No documents found
            {labelFilter && ` with label "${labelFilter.replace(/_/g, " ")}"`}
            {colorFilter && ` with ${colorFilter} color`}.
          </div>
        )}

        {/* Document cards */}
        {predictions?.map((pred, idx) => {
          const borderColor = cardBorderColor(pred);
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
                gridTemplateColumns: "1fr 150px 100px 90px 140px auto",
                gap: "0.75rem", alignItems: "center",
                padding: "0.75rem 1rem 0.75rem 1rem",
              }}>
                {/* Doc name */}
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", minWidth: 0 }}>
                  <ColorDot color={pred.comment_color} size={8} />
                  <code style={{
                    fontSize: "13px",
                    color: "var(--text)",
                    fontFamily: "var(--font-mono)",
                    fontWeight: "500",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>
                    {docName(pred)}
                  </code>
                </div>

                {/* Label — editable for admin/reviewer */}
                <div>
                  {canEdit && editingLabel === pred.id ? (
                    <select
                      autoFocus
                      className="select"
                      defaultValue={pred.label}
                      disabled={relabelMutation.isPending}
                      style={{ fontSize: "13px", padding: "0.2rem 0.5rem" }}
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
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2.5" style={{ flexShrink: 0, opacity: 0.6 }}>
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                      )}
                    </div>
                  )}
                </div>

                {/* Confidence */}
                <ConfidencePill value={pred.top1_confidence} />

                {/* Latency */}
                <LatencyPill ms={pred.latency_ms} />

                {/* Date */}
                <span style={{ fontSize: "13px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                  {formatDate(pred.created_at)}
                </span>

                {/* Actions */}
                <div style={{ display: "flex", gap: "0.2rem", alignItems: "center" }}>
                  {/* View */}
                  <button
                    title="View document"
                    onClick={() => setViewingPred(pred)}
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      color: "var(--text-dim)", padding: "0.3rem", borderRadius: "4px",
                      display: "flex", alignItems: "center",
                      transition: "color 0.12s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.color = "var(--accent)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.color = "var(--text-dim)"}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  </button>

                  {/* Comment */}
                  {canEdit && (
                    <button
                      title={pred.comment ? "Edit note" : "Add note"}
                      onClick={() => {
                        setEditingComment(editingComment === pred.id ? null : pred.id);
                        setEditingColor(null);
                      }}
                      style={{
                        background: "none", border: "none", cursor: "pointer",
                        color: pred.comment ? "var(--accent-warm)" : "var(--text-dim)",
                        padding: "0.3rem", borderRadius: "4px",
                        display: "flex", alignItems: "center",
                        transition: "color 0.12s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.color = "var(--accent-warm)"}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.color = pred.comment ? "var(--accent-warm)" : "var(--text-dim)";
                      }}
                    >
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                      </svg>
                    </button>
                  )}

                  {/* Card color */}
                  {canEdit && (
                    <button
                      title="Set card color"
                      onClick={() => {
                        setEditingColor(editingColor === pred.id ? null : pred.id);
                        setEditingComment(null);
                      }}
                      style={{
                        background: "none", border: "none", cursor: "pointer",
                        color: pred.comment_color ? COMMENT_COLORS.find(c => c.value === pred.comment_color)?.hex ?? "var(--text-dim)" : "var(--text-dim)",
                        padding: "0.3rem", borderRadius: "4px",
                        display: "flex", alignItems: "center",
                        transition: "color 0.12s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.color = "var(--accent)"}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.color = pred.comment_color
                          ? COMMENT_COLORS.find(c => c.value === pred.comment_color)?.hex ?? "var(--text-dim)"
                          : "var(--text-dim)";
                      }}
                    >
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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

              {/* Card color picker (inline) */}
              {canEdit && editingColor === pred.id && (
                <CardColorPicker
                  prediction={pred}
                  onSave={(color) => applyCardColor(pred, color)}
                  onCancel={() => setEditingColor(null)}
                  isSaving={commentMutation.isPending}
                />
              )}

              {/* Comment display */}
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
                  <span style={{ fontSize: "14px", color: "var(--text)", lineHeight: 1.5 }}>
                    {pred.comment}
                  </span>
                </div>
              )}

              {/* Comment editor */}
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

      {/* Bottom pagination — only shown when there are results */}
      {(predictions?.length ?? 0) > 0 && (
        <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: "0.5rem", marginTop: "1.25rem" }}>
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
            color: "var(--text-muted)",
            minWidth: "64px",
            textAlign: "center",
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
      )}
    </Layout>
  );
}
