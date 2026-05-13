import type { BatchStatus } from "../api/types";

export function StatusBadge({ status }: { status: BatchStatus }) {
  const map: Record<BatchStatus, { color: string; bg: string }> = {
    complete:   { color: "var(--success)",    bg: "rgba(16,185,129,0.12)" },
    processing: { color: "var(--accent)",     bg: "var(--accent-glow)"    },
    pending:    { color: "var(--text-muted)", bg: "rgba(82,97,130,0.15)"  },
    failed:     { color: "var(--danger)",     bg: "rgba(239,68,68,0.12)"  },
  };
  const s = map[status];

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        padding: "0.25rem 0.7rem",
        borderRadius: "20px",
        fontSize: "13px",
        fontFamily: "var(--font-mono)",
        fontWeight: "500",
        letterSpacing: "0.03em",
        color: s.color,
        background: s.bg,
      }}
    >
      <span
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          background: s.color,
          flexShrink: 0,
        }}
      />
      {status}
    </span>
  );
}
