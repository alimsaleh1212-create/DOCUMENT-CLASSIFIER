import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { StatusBadge } from "../components/StatusBadge";
import client from "../api/client";
import type { BatchOut } from "../api/types";

export default function BatchesListPage() {
  const [cacheStatus, setCacheStatus] = useState<string | null>(null);

  const { data: batches, isLoading, isError, refetch } = useQuery<BatchOut[]>({
    queryKey: ["batches"],
    queryFn: async () => {
      const res = await client.get<BatchOut[]>("/batches");
      setCacheStatus((res.headers as Record<string, string>)["x-cache"] ?? null);
      return res.data;
    },
    staleTime: 30_000,
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const actions = (
    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
      {cacheStatus && (
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            padding: "0.2rem 0.6rem",
            borderRadius: "20px",
            fontSize: "12px",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: cacheStatus === "HIT" ? "var(--success)" : "var(--text-muted)",
            background:
              cacheStatus === "HIT" ? "rgba(16,185,129,0.1)" : "rgba(82,97,130,0.15)",
            border: `1px solid ${cacheStatus === "HIT" ? "rgba(16,185,129,0.2)" : "var(--border)"}`,
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: cacheStatus === "HIT" ? "var(--success)" : "var(--text-muted)",
            }}
          />
          Cache {cacheStatus}
        </span>
      )}
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => void refetch()}
        disabled={isLoading}
      >
        ↺ Refresh
      </button>
    </div>
  );

  return (
    <Layout
      title="Batches"
      subtitle="Document batches submitted for classification"
      actions={actions}
    >
      {isError && (
        <div
          style={{
            padding: "1rem 1.25rem",
            background: "rgba(239,68,68,0.06)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "var(--radius)",
            color: "var(--danger)",
            fontSize: "15px",
          }}
        >
          Failed to load batches.
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Batch ID</th>
              <th>Status</th>
              <th>Documents</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <td key={j}>
                      <div
                        className="skeleton"
                        style={{ height: "16px", width: j === 0 ? "180px" : j === 2 ? "40px" : "80px" }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            {!isLoading && batches?.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)", padding: "2.5rem" }}>
                  No batches yet.
                </td>
              </tr>
            )}
            {batches?.map((batch, idx) => (
              <tr
                key={batch.id}
                className="animate-fade-up"
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                <td>
                  <code
                    className="mono"
                    style={{ fontSize: "13px", color: "var(--text-muted)" }}
                  >
                    {batch.id.slice(0, 8)}…
                  </code>
                </td>
                <td>
                  <StatusBadge status={batch.status} />
                </td>
                <td>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "15px",
                      color: "var(--text)",
                    }}
                  >
                    {batch.document_count}
                  </span>
                </td>
                <td style={{ color: "var(--text-muted)", fontSize: "14px" }}>
                  {formatDate(batch.created_at)}
                </td>
                <td style={{ textAlign: "right" }}>
                  <Link
                    to={`/batches/${batch.id}`}
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: "14px" }}
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
