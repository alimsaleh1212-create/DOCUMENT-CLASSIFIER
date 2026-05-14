import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Layout } from "../components/Layout";
import client from "../api/client";
import type { AuditLogEntry } from "../api/types";

const PAGE_SIZE = 20;

const ACTION_COLORS: Record<string, string> = {
  role_change:     "var(--role-admin)",
  relabel:         "var(--accent-warm)",
  batch_state:     "var(--accent)",
  add_comment:     "var(--role-reviewer)",
  delete_user:     "var(--danger)",
  rename_document: "var(--role-auditor)",
};

function ActionChip({ action }: { action: string }) {
  const color = ACTION_COLORS[action] ?? "var(--text-muted)";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.2rem 0.55rem",
        borderRadius: "5px",
        fontSize: "13px",
        fontFamily: "var(--font-mono)",
        fontWeight: 600,
        letterSpacing: "0.04em",
        color,
        background: `${color}1a`,
        border: `1px solid ${color}30`,
      }}
    >
      {action.replace(/_/g, " ")}
    </span>
  );
}

function ActorCell({ entry }: { entry: AuditLogEntry }) {
  if (entry.actor_id === "system" || !entry.actor_id) {
    return (
      <span style={{ color: "var(--text-muted)", fontStyle: "italic", fontSize: "14px" }}>
        system
      </span>
    );
  }
  if (entry.actor_email) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <div
          style={{
            width: "24px", height: "24px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, var(--accent), #818CF8)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "11px",
            color: "#06080F",
            flexShrink: 0,
          }}
        >
          {entry.actor_email[0].toUpperCase()}
        </div>
        <span style={{ fontSize: "14px", color: "#E8F0FF", fontWeight: 500 }}>
          {entry.actor_email}
        </span>
      </div>
    );
  }
  return (
    <code style={{ fontSize: "13px", color: "#C8D4EA", fontFamily: "var(--font-mono)" }}>
      {entry.actor_id.slice(0, 8)}…
    </code>
  );
}

function MetadataCell({ metadata }: { metadata: Record<string, unknown> | null }) {
  if (!metadata) {
    return <span style={{ color: "var(--text-dim)" }}>—</span>;
  }
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
      {Object.entries(metadata).map(([k, v]) => (
        <span
          key={k}
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            padding: "0.15rem 0.45rem",
            borderRadius: "4px",
            background: "var(--bg-raised)",
            border: "1px solid var(--border-subtle)",
            color: "#E8F0FF",
            whiteSpace: "nowrap",
            maxWidth: "260px",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
          title={`${k}: ${String(v)}`}
        >
          <span style={{ color: "#7A8DAE" }}>{k}:</span>{" "}
          <span style={{ color: "#E8F0FF", fontWeight: 500 }}>{String(v)}</span>
        </span>
      ))}
    </div>
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
      <button className="btn btn-ghost btn-sm" onClick={() => setPage((p) => p - 1)} disabled={!hasPrev}>
        ← Prev
      </button>
      <span
        style={{
          fontSize: "14px",
          fontFamily: "var(--font-mono)",
          color: "#E8F0FF",
          minWidth: "64px",
          textAlign: "center",
          fontWeight: 500,
        }}
      >
        Page {page}
      </span>
      <button className="btn btn-ghost btn-sm" onClick={() => setPage((p) => p + 1)} disabled={!hasNext}>
        Next →
      </button>
    </div>
  );

  return (
    <Layout title="Audit Log" subtitle="All recorded actions in the system">
      {isError && (
        <div
          style={{
            padding: "1rem",
            background: "rgba(239,68,68,0.06)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "var(--radius)",
            color: "var(--danger)",
            fontSize: "15px",
          }}
        >
          Failed to load audit log.
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table audit-table" style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={auditHeaderStyle}>Timestamp</th>
              <th style={auditHeaderStyle}>Actor</th>
              <th style={auditHeaderStyle}>Action</th>
              <th style={auditHeaderStyle}>Target</th>
              <th style={auditHeaderStyle}>Metadata</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <td key={j} style={{ padding: "0.875rem 1.1rem" }}>
                      <div className="skeleton" style={{ height: "14px", width: j === 4 ? "180px" : "100px" }} />
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
                style={{
                  animationDelay: `${idx * 25}ms`,
                  borderBottom: "1px solid var(--border-subtle)",
                }}
              >
                <td style={auditCellStyle}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "#C8D4EA", whiteSpace: "nowrap" }}>
                    {formatTime(entry.timestamp)}
                  </span>
                </td>
                <td style={auditCellStyle}>
                  <ActorCell entry={entry} />
                </td>
                <td style={auditCellStyle}>
                  <ActionChip action={entry.action} />
                </td>
                <td style={auditCellStyle}>
                  <code className="mono" style={{ fontSize: "13px", color: "#E8F0FF" }}>
                    {entry.target.slice(0, 12)}…
                  </code>
                </td>
                <td style={auditCellStyle}>
                  <MetadataCell metadata={entry.metadata} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {(data?.length ?? 0) > 0 && (
          <div
            style={{
              padding: "0.85rem 1.1rem",
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

const auditHeaderStyle: React.CSSProperties = {
  padding: "0.85rem 1.1rem",
  textAlign: "left",
  fontFamily: "var(--font-display)",
  fontSize: "13px",
  fontWeight: 600,
  letterSpacing: "0.04em",
  color: "#E8F0FF",
  borderBottom: "1px solid var(--border)",
  whiteSpace: "nowrap",
  background: "var(--bg-raised)",
};

const auditCellStyle: React.CSSProperties = {
  padding: "0.9rem 1.1rem",
  color: "#E8F0FF",
  verticalAlign: "middle",
};
