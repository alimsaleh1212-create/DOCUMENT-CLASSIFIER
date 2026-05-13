import type { PredictionLabel } from "../api/types";

const LABEL_ICONS: Record<PredictionLabel, string> = {
  letter: "✉",
  form: "📋",
  email: "📧",
  handwritten: "✍",
  advertisement: "📢",
  scientific_report: "🔬",
  scientific_publication: "📰",
  specification: "📐",
  file_folder: "📁",
  news_article: "📄",
  budget: "💰",
  invoice: "🧾",
  presentation: "📊",
  questionnaire: "❓",
  resume: "👤",
  memo: "📝",
};

export function LabelBadge({ label }: { label: PredictionLabel }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        padding: "0.2rem 0.5rem",
        borderRadius: "var(--radius)",
        background: "rgba(34,211,238,0.08)",
        border: "1px solid rgba(34,211,238,0.15)",
        color: "var(--accent)",
        fontSize: "11px",
        fontFamily: "var(--font-mono)",
        fontWeight: "500",
        letterSpacing: "0.02em",
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ fontSize: "12px" }}>{LABEL_ICONS[label]}</span>
      {label.replace(/_/g, " ")}
    </span>
  );
}
