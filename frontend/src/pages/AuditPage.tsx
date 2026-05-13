import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layout } from "../components/Layout";
import client from "../api/client";
import type { AuditLogEntry } from "../api/types";

const PAGE_SIZE = 20;

const ACTION_COLORS: Record<string, string> = {
  role_change:  "var(--role-admin)",
  relabel:      "var(--accent-warm)",
  batch_state:  "var(--accent)",
};

function ActionChip({ action }: { action: string }) {
  const color = ACTION_COLORS[action] ?? "var(--text-muted)";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.15rem 0.5rem",
        borderRadius: "4px",
        fontSize: "11px",
        fontFamily: "var(--font-mono)",
        fontWeight: "500",
        letterSpacing: "0.04em",
        color,
        background: `${color}18`,
        border: `1px solid ${color}28`,
      }}
    >
      {action.replace(/_/g, " ")}
    </span>
  );
}

export default function AuditPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery<AuditLogEntry[]>({
    queryKey: ["audit", page],
    queryFn: async () => {
      const res = await client.get<AuditLogEntry[]>("/audit", {
        params: { page, limit: PAGE_SIZE },
      });
      return res.data;
    },
    staleTime: 15_000,
    placeholderData: (prev) => prev,
  });

  const hasNext = (data?.length ?? 0) >= PAGE_SIZE;
  const hasPrev = page > 1;

  function formatTime(iso: string) {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  }

  const pagination = (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => setPage((p) => p - 1)}
        disabled={!hasPrev}
      >
        ← Prev
      </button>
      <span
        style={{
          fontSize: "12px",
          fontFamily: "var(--font-mono)",
          color: "var(--text-muted)",
          minWidth: "60px",
          textAlign: "center",
        }}
      >
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
  );

  return (
    <Layout
      title="Audit Log"
      subtitle="All recorded actions in the system"
      actions={pagination}
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
          Failed to load audit log.
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th>Metadata</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <td key={j}>
                      <div className="skeleton" style={{ height: "14px", width: j === 4 ? "120px" : "90px" }} />
                    </td>
                  ))}
                </tr>
              ))}
            {!isLoading && data?.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)", padding: "2.5rem" }}>
                  No audit entries yet.
                </td>
              </tr>
            )}
            {data?.map((entry, idx) => (
              <tr
                key={entry.id}
                className="animate-fade-up"
                style={{ animationDelay: `${idx * 25}ms` }}
              >
                <td>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                    {formatTime(entry.timestamp)}
                  </span>
                </td>
                <td>
                  <code className="mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {entry.actor_id === "system" ? (
                      <span style={{ color: "var(--text-dim)" }}>system</span>
                    ) : (
                      entry.actor_id.slice(0, 8) + "…"
                    )}
                  </code>
                </td>
                <td>
                  <ActionChip action={entry.action} />
                </td>
                <td>
                  <code className="mono" style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    {entry.target.slice(0, 12)}…
                  </code>
                </td>
                <td>
                  {entry.metadata ? (
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--text-dim)" }}>
                      {Object.entries(entry.metadata)
                        .map(([k, v]) => `${k}: ${String(v)}`)
                        .join(" · ")}
                    </span>
                  ) : (
                    <span style={{ color: "var(--text-dim)" }}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Bottom pagination */}
        {(data?.length ?? 0) > 0 && (
          <div
            style={{
              padding: "0.75rem 1rem",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              justifyContent: "flex-end",
            }}
          >
            {pagination}
          </div>
        )}
      </div>
    </Layout>
  );
}
