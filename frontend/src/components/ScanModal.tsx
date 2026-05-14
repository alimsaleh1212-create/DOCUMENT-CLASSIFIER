import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "../api/client";
import type { GoldenFile } from "../api/types";

interface ScanModalProps {
  onClose: () => void;
}

export default function ScanModal({ onClose }: ScanModalProps) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<{ queued: string[]; failed: string[] } | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const autoCloseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: files, isLoading } = useQuery<GoldenFile[]>({
    queryKey: ["scan-golden"],
    queryFn: async () => {
      const res = await client.get<GoldenFile[]>("/scan/golden");
      return res.data;
    },
    staleTime: 60_000,
  });

  const triggerMutation = useMutation({
    mutationFn: async (fileNames: string[]) => {
      const res = await client.post<{ queued: string[]; failed: string[] }>("/scan/trigger", {
        files: fileNames,
      });
      return res.data;
    },
    onSuccess: (data) => {
      setResult(data);
      setApiError(null);
      // Invalidate predictions queries so the Documents page refreshes
      void queryClient.invalidateQueries({ queryKey: ["predictions"] });
      // Auto-close after 2.5s if all queued (pipeline will deliver results in ~10s)
      if (data.queued.length > 0) {
        autoCloseTimer.current = setTimeout(() => {
          onClose();
          // Schedule a second invalidation after pipeline latency (~12s)
          setTimeout(() => {
            void queryClient.invalidateQueries({ queryKey: ["predictions"] });
          }, 12_000);
        }, 2500);
      }
    },
    onError: (err: { response?: { data?: { detail?: string }; status?: number } }) => {
      const detail =
        err?.response?.data?.detail ??
        (err?.response?.status === 502
          ? "SFTP connection failed. Is the sftp-ingest service running?"
          : "Upload failed. Check the server logs.");
      setApiError(detail);
      setResult(null);
    },
  });

  // Clean up auto-close timer on unmount
  useEffect(() => {
    return () => {
      if (autoCloseTimer.current) clearTimeout(autoCloseTimer.current);
    };
  }, []);

  function toggle(name: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function selectAll() {
    setSelected(new Set(files?.map((f) => f.name) ?? []));
  }

  function clearAll() {
    setSelected(new Set());
  }

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        background: "rgba(6,8,15,0.82)",
        backdropFilter: "blur(8px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "1rem",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="animate-fade-up"
        style={{
          width: "100%", maxWidth: "480px",
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          overflow: "hidden",
          boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
        }}
      >
        {/* Header */}
        <div style={{
          padding: "1.25rem 1.5rem",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
            <div style={{
              width: "32px", height: "32px",
              background: "var(--accent-glow)",
              border: "1px solid var(--accent)",
              borderRadius: "var(--radius)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="3" y1="15" x2="21" y2="15"/>
                <line x1="9" y1="3" x2="9" y2="9"/>
                <line x1="15" y1="3" x2="15" y2="9"/>
              </svg>
            </div>
            <div>
              <h3 style={{ fontSize: "16px", fontFamily: "var(--font-display)", margin: 0, color: "#E8F0FF" }}>
                Scan Documents
              </h3>
              <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: 0 }}>
                Select golden images to send via SFTP pipeline
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", cursor: "pointer",
              color: "var(--text-muted)", padding: "0.25rem", borderRadius: "4px",
              display: "flex", alignItems: "center",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* File list */}
        <div style={{ maxHeight: "320px", overflowY: "auto", padding: "0.75rem 1rem" }}>
          {isLoading && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton" style={{ height: "36px", borderRadius: "var(--radius)" }} />
              ))}
            </div>
          )}
          {!isLoading && files?.length === 0 && (
            <p style={{ color: "var(--text-muted)", fontSize: "14px", textAlign: "center", padding: "1rem 0" }}>
              No golden images found in the eval directory.
            </p>
          )}
          {files?.map((file) => (
            <label
              key={file.name}
              style={{
                display: "flex", alignItems: "center", gap: "0.75rem",
                padding: "0.55rem 0.75rem",
                borderRadius: "var(--radius)",
                cursor: "pointer",
                transition: "background 0.12s",
                background: selected.has(file.name) ? "var(--accent-glow)" : "transparent",
                border: selected.has(file.name) ? "1px solid rgba(34,211,238,0.25)" : "1px solid transparent",
                marginBottom: "0.25rem",
              }}
              onMouseEnter={(e) => {
                if (!selected.has(file.name))
                  (e.currentTarget as HTMLElement).style.background = "var(--bg-raised)";
              }}
              onMouseLeave={(e) => {
                if (!selected.has(file.name))
                  (e.currentTarget as HTMLElement).style.background = "transparent";
              }}
            >
              <input
                type="checkbox"
                checked={selected.has(file.name)}
                onChange={() => toggle(file.name)}
                style={{ accentColor: "var(--accent)", width: "15px", height: "15px", flexShrink: 0 }}
              />
              <span style={{ flex: 1, fontSize: "14px", fontFamily: "var(--font-mono)", color: "var(--text)" }}>
                {file.name}
              </span>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                {file.size_kb} KB
              </span>
            </label>
          ))}
        </div>

        {/* Select all / clear */}
        {files && files.length > 0 && (
          <div style={{
            padding: "0.5rem 1rem",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex", gap: "0.5rem",
          }}>
            <button className="btn btn-ghost btn-sm" onClick={selectAll} style={{ fontSize: "12px" }}>
              Select all
            </button>
            <button className="btn btn-ghost btn-sm" onClick={clearAll} style={{ fontSize: "12px" }}>
              Clear
            </button>
            <span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--text-muted)", alignSelf: "center" }}>
              {selected.size} selected
            </span>
          </div>
        )}

        {/* Error banner */}
        {apiError && (
          <div style={{
            margin: "0 1rem 0.75rem",
            padding: "0.75rem 1rem",
            borderRadius: "var(--radius)",
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.25)",
            fontSize: "14px",
            color: "var(--danger)",
          }}>
            <strong>Error:</strong> {apiError}
          </div>
        )}

        {/* Success result banner */}
        {result && (
          <div style={{
            margin: "0 1rem 0.75rem",
            padding: "0.75rem 1rem",
            borderRadius: "var(--radius)",
            background: result.failed.length === 0
              ? "rgba(16,185,129,0.08)"
              : "rgba(245,158,11,0.08)",
            border: `1px solid ${result.failed.length === 0 ? "rgba(16,185,129,0.25)" : "rgba(245,158,11,0.25)"}`,
            fontSize: "14px",
          }}>
            {result.queued.length > 0 && (
              <p style={{ margin: 0, color: "var(--success)", fontWeight: 600 }}>
                {result.queued.length} file{result.queued.length !== 1 ? "s" : ""} sent to pipeline
              </p>
            )}
            {result.failed.length > 0 && (
              <p style={{ margin: "0.25rem 0 0", color: "var(--warning)" }}>
                {result.failed.length} file{result.failed.length !== 1 ? "s" : ""} failed to upload
              </p>
            )}
            {result.queued.length > 0 && (
              <p style={{ margin: "0.4rem 0 0", fontSize: "12px", color: "var(--text-muted)" }}>
                Closing automatically… Results will appear in Documents within ~10s.
              </p>
            )}
          </div>
        )}

        {/* Footer actions */}
        <div style={{
          padding: "1rem 1.5rem",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex", justifyContent: "flex-end", gap: "0.625rem",
        }}>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            {result ? "Close" : "Cancel"}
          </button>
          {!result && (
            <button
              className="btn btn-sm"
              disabled={selected.size === 0 || triggerMutation.isPending}
              onClick={() => {
                setApiError(null);
                triggerMutation.mutate([...selected]);
              }}
              style={{
                background: selected.size === 0 ? "var(--bg-raised)" : "var(--accent)",
                color: selected.size === 0 ? "var(--text-dim)" : "#06080F",
                fontWeight: "600",
                opacity: triggerMutation.isPending ? 0.7 : 1,
                cursor: selected.size === 0 ? "not-allowed" : "pointer",
                transition: "all 0.15s",
              }}
            >
              {triggerMutation.isPending ? (
                <span style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: "spin 1s linear infinite" }}>
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                  </svg>
                  Sending…
                </span>
              ) : (
                `Send${selected.size > 0 ? ` (${selected.size})` : ""}`
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
