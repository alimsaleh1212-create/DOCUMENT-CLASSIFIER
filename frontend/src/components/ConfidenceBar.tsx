interface ConfidenceBarProps {
  value: number;
  width?: number;
}

export function ConfidenceBar({ value, width = 80 }: ConfidenceBarProps) {
  const pct = Math.min(1, Math.max(0, value));
  const color =
    pct >= 0.7
      ? "var(--success)"
      : pct >= 0.4
        ? "var(--warning)"
        : "var(--danger)";

  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
      <div
        className="conf-bar-track"
        style={{ width: `${width}px` }}
        title={`${(pct * 100).toFixed(1)}%`}
      >
        <div
          className="conf-bar-fill"
          style={{
            width: `${pct * 100}%`,
            background: color,
          }}
        />
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          color,
          minWidth: "38px",
        }}
      >
        {(pct * 100).toFixed(1)}%
      </span>
    </div>
  );
}
