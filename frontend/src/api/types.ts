export type Role = "admin" | "reviewer" | "auditor";

export type BatchStatus = "pending" | "processing" | "complete" | "failed";

export type PredictionLabel =
  | "letter"
  | "form"
  | "email"
  | "handwritten"
  | "advertisement"
  | "scientific_report"
  | "scientific_publication"
  | "specification"
  | "file_folder"
  | "news_article"
  | "budget"
  | "invoice"
  | "presentation"
  | "questionnaire"
  | "resume"
  | "memo";

export const PREDICTION_LABELS: PredictionLabel[] = [
  "letter",
  "form",
  "email",
  "handwritten",
  "advertisement",
  "scientific_report",
  "scientific_publication",
  "specification",
  "file_folder",
  "news_article",
  "budget",
  "invoice",
  "presentation",
  "questionnaire",
  "resume",
  "memo",
];

export interface UserOut {
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface BatchOut {
  id: string;
  status: BatchStatus;
  document_count: number;
  created_at: string;
}

export interface PredictionOut {
  id: string;
  batch_id: string;
  document_id: string;
  label: PredictionLabel;
  top1_confidence: number;
  top5: [PredictionLabel, number][];
  overlay_url: string | null;
  model_version: string;
  created_at: string;
  latency_ms: number | null;
  comment: string | null;
  comment_color: string | null;
  document_name: string | null;
}

export interface GoldenFile {
  name: string;
  size_kb: number;
}

export const COMMENT_COLORS = [
  { value: "blue",   label: "Blue",   hex: "#3B82F6" },
  { value: "green",  label: "Green",  hex: "#10B981" },
  { value: "amber",  label: "Amber",  hex: "#F59E0B" },
  { value: "red",    label: "Red",    hex: "#EF4444" },
  { value: "purple", label: "Purple", hex: "#A78BFA" },
  { value: "cyan",   label: "Cyan",   hex: "#22D3EE" },
];

export interface AuditLogEntry {
  id: string;
  actor_id: string;
  actor_email: string | null;
  action: string;
  target: string;
  metadata: Record<string, unknown> | null;
  timestamp: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  id: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}
