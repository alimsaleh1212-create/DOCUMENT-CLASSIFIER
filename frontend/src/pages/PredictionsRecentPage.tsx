import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { LabelBadge } from "../components/LabelBadge";
import { ConfidenceBar } from "../components/ConfidenceBar";
import client from "../api/client";
import type { PredictionOut } from "../api/types";

export default function PredictionsRecentPage() {
  const { data: predictions, isLoading, isError } = useQuery<PredictionOut[]>({
    queryKey: ["predictions", "recent"],
    queryFn: async () => {
      const res = await client.get<PredictionOut[]>("/predictions/recent");
      return res.data;
    },
    staleTime: 15_000,
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <Layout
      title="Recent Predictions"
      subtitle="Latest classification results across all batches"
    >
      {isError && (
        <div
          style={{
            padding: "1rem",
            background: "rgba(239,68,68,0.06)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "var(--radius)",
            color: "var(--danger)",
            fontSize: "13px",
          }}
        >
          Failed to load predictions.
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Label</th>
              <th>Confidence</th>
              <th>Batch</th>
              <th>Model</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j}>
                      <div className="skeleton" style={{ height: "14px", width: j === 1 ? "100px" : "80px" }} />
                    </td>
                  ))}
                </tr>
              ))}
            {!isLoading && predictions?.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)", padding: "2.5rem" }}>
                  No predictions yet.
                </td>
              </tr>
            )}
            {predictions?.map((pred, idx) => (
              <tr
                key={pred.id}
                className="animate-fade-up"
                style={{ animationDelay: `${idx * 30}ms` }}
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
                  <Link
                    to={`/batches/${pred.batch_id}`}
                    style={{ color: "var(--accent)", fontSize: "12px", textDecoration: "none", fontFamily: "var(--font-mono)" }}
                  >
                    {pred.batch_id.slice(0, 8)}…
                  </Link>
                </td>
                <td>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)" }}>
                    {pred.model_version}
                  </span>
                </td>
                <td style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                  {formatDate(pred.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
