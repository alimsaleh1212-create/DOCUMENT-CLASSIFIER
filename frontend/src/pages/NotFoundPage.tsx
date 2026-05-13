import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "1rem",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "72px",
          fontWeight: "500",
          color: "var(--border)",
          lineHeight: 1,
          letterSpacing: "-0.04em",
        }}
      >
        404
      </div>
      <h1
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "20px",
          color: "var(--text)",
          fontWeight: "600",
        }}
      >
        Page not found
      </h1>
      <p style={{ color: "var(--text-muted)", fontSize: "14px", maxWidth: "320px", margin: 0 }}>
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/batches" className="btn btn-ghost" style={{ marginTop: "0.5rem" }}>
        ← Back to batches
      </Link>
    </div>
  );
}
