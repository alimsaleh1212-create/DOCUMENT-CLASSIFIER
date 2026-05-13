import type { BatchStatus } from "../api/types";

export function StatusBadge({ status }: { status: BatchStatus }) {
  const map: Record<BatchStatus, { color: string; bg: string; dot: string }> = {
    complete:   { color: "var(--success)",     bg: "rgba(16,185,129,0.12)",  dot: "var(--success)" },
    processing: { color: "var(--accent)",      bg: "var(--accent-glow)",     dot: "var(--accent)" },
    pending:    { color: "var(--text-muted)",  bg: "rgba(82,97,130,0.15)",   dot: "var(--text-muted)" },
    failed:     { color: "var(--danger)",      bg: "rgba(239,68,68,0.12)",   dot: "var(--danger)" },
  };
  const s = map[status];

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding: "0.2rem 0.6rem",
        borderRadius: "20px",
        fontSize: "11px",
        fontFamily: "var(--font-mono)",
        fontWeight: "500",
        letterSpacing: "0.04em",
        color: s.color,
        background: s.bg,
      }}
    >
      <span
        style={{
          width: "5px",
          height: "5px",
          borderRadius: "50%",
          background: s.dot,
          flexShrink: 0,
          animation: status === "processing" ? "pulse-glow 1.5s ease infinite" : "none",
        }}
      />
      {status}
    </span>
  );
}
