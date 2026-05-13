import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Layout } from "../components/Layout";
import { StatusBadge } from "../components/StatusBadge";
import { LabelBadge } from "../components/LabelBadge";
import { ConfidenceBar } from "../components/ConfidenceBar";
import { Toast } from "../components/Toast";
import { getRole } from "../hooks/useAuth";
import client from "../api/client";
import type { BatchOut, PredictionOut, PredictionLabel } from "../api/types";
import { PREDICTION_LABELS } from "../api/types";

export default function BatchDetailPage() {
  const { bid } = useParams<{ bid: string }>();
  const queryClient = useQueryClient();
  const role = getRole();
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  const [relabelingId, setRelabelingId] = useState<string | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<PredictionLabel>("letter");

  const { data: batch, isLoading: batchLoading } = useQuery<BatchOut>({
    queryKey: ["batches", bid],
    queryFn: async () => {
      const res = await client.get<BatchOut>(`/batches/${bid}`);
      return res.data;
    },
    enabled: !!bid,
  });

  const { data: allPredictions, isLoading: predsLoading } = useQuery<PredictionOut[]>({
    queryKey: ["predictions", "recent"],
    queryFn: async () => {
      const res = await client.get<PredictionOut[]>("/predictions/recent");
      return res.data;
    },
    staleTime: 15_000,
  });

  const predictions = allPredictions?.filter((p) => p.batch_id === bid) ?? [];

  const relabelMutation = useMutation({
    mutationFn: async ({ pid, label }: { pid: string; label: PredictionLabel }) => {
      const res = await client.patch<PredictionOut>(`/predictions/${pid}/label`, {
        new_label: label,
      });
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["predictions", "recent"] });
      void queryClient.invalidateQueries({ queryKey: ["batches", bid] });
      setRelabelingId(null);
      setToast({ msg: "Label updated successfully.", type: "success" });
    },
    onError: (err: Error) => {
      setToast({ msg: err.message || "Relabel failed.", type: "error" });
    },
  });

  const isLoading = batchLoading || predsLoading;

  return (
    <Layout
      title={batch ? `Batch ${batch.id.slice(0, 8)}…` : "Loading…"}
      subtitle={batch ? `${batch.document_count} document${batch.document_count !== 1 ? "s" : ""}` : undefined}
      actions={
        <Link to="/batches" className="btn btn-ghost btn-sm">
          ← All batches
        </Link>
      }
    >
      {toast && (
        <Toast
          message={toast.msg}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Batch metadata */}
      {batch && (
        <div
          className="animate-fade-up"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: "0.75rem",
            marginBottom: "1.5rem",
          }}
        >
          {[
            { label: "Status",    value: <StatusBadge status={batch.status} /> },
            { label: "Documents", value: <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent)" }}>{batch.document_count}</span> },
            { label: "Created",   value: new Date(batch.created_at).toLocaleDateString() },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                padding: "0.875rem 1rem",
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
              }}
            >
              <div style={{ fontSize: "10px", fontFamily: "var(--font-mono)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-dim)", marginBottom: "0.375rem" }}>
                {item.label}
              </div>
              <div>{item.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Predictions table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div
          style={{
            padding: "0.875rem 1rem",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span style={{ fontFamily: "var(--font-display)", fontWeight: "600", fontSize: "14px" }}>
            Predictions
          </span>
          <span style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {isLoading ? "…" : `${predictions.length} result${predictions.length !== 1 ? "s" : ""}`}
          </span>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Label</th>
              <th>Confidence</th>
              <th>Model</th>
              <th>Overlay</th>
              {role === "reviewer" && <th>Action</th>}
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: role === "reviewer" ? 6 : 5 }).map((_, j) => (
                    <td key={j}>
                      <div className="skeleton" style={{ height: "16px", width: j === 0 ? "140px" : "80px" }} />
                    </td>
                  ))}
                </tr>
              ))}
            {!isLoading && predictions.length === 0 && (
              <tr>
                <td colSpan={role === "reviewer" ? 6 : 5} style={{ textAlign: "center", color: "var(--text-muted)", padding: "2.5rem" }}>
                  No predictions for this batch yet.
                </td>
              </tr>
            )}
            {predictions.map((pred, idx) => (
              <tr
                key={pred.id}
                className="animate-fade-up"
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                <td>
                  <code className="mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {pred.document_id.slice(0, 8)}…
                  </code>
                </td>
                <td>
                  <LabelBadge label={pred.label} />
                </td>
                <td>
                  <ConfidenceBar value={pred.top1_confidence} />
                </td>
                <td>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                    {pred.model_version}
                  </span>
                </td>
                <td>
                  {pred.overlay_url ? (
                    <a
                      href={pred.overlay_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: "var(--accent)", fontSize: "12px", textDecoration: "none" }}
                    >
                      View ↗
                    </a>
                  ) : (
                    <span style={{ color: "var(--text-dim)", fontSize: "12px" }}>—</span>
                  )}
                </td>

                {role === "reviewer" && (
                  <td>
                    {pred.top1_confidence < 0.7 ? (
                      relabelingId === pred.id ? (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <select
                            className="select"
                            value={selectedLabel}
                            onChange={(e) => setSelectedLabel(e.target.value as PredictionLabel)}
                          >
                            {PREDICTION_LABELS.map((lbl) => (
                              <option key={lbl} value={lbl}>
                                {lbl.replace(/_/g, " ")}
                              </option>
                            ))}
                          </select>
                          <button
                            className="btn btn-primary btn-sm"
                            disabled={relabelMutation.isPending}
                            onClick={() => relabelMutation.mutate({ pid: pred.id, label: selectedLabel })}
                          >
                            {relabelMutation.isPending ? (
                              <span className="spinner" style={{ width: "12px", height: "12px" }} />
                            ) : "Save"}
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => setRelabelingId(null)}
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{ color: "var(--accent-warm)", borderColor: "rgba(245,158,11,0.25)" }}
                          onClick={() => {
                            setRelabelingId(pred.id);
                            setSelectedLabel(pred.label);
                          }}
                        >
                          Relabel
                        </button>
                      )
                    ) : (
                      <span
                        style={{
                          fontSize: "11px",
                          color: "var(--text-dim)",
                          fontFamily: "var(--font-mono)",
                        }}
                        title="Confidence ≥ 0.7: relabeling not allowed"
                      >
                        locked
                      </span>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
