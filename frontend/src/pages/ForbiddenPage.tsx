import { Link } from "react-router-dom";

interface ForbiddenPageProps {
  requiredRole?: string;
}

export default function ForbiddenPage({ requiredRole }: ForbiddenPageProps) {
  return (
    <div
      style={{
        minHeight: "60vh",
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
          width: "56px",
          height: "56px",
          borderRadius: "50%",
          background: "rgba(239,68,68,0.1)",
          border: "1px solid rgba(239,68,68,0.25)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "24px",
        }}
      >
        ⚠
      </div>
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "18px",
          color: "var(--text)",
          fontWeight: "700",
          margin: 0,
        }}
      >
        Access denied
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "13px", margin: 0 }}>
        {requiredRole
          ? `This page requires the "${requiredRole}" role.`
          : "You don't have permission to view this page."}
      </p>
      <Link to="/batches" className="btn btn-ghost" style={{ marginTop: "0.25rem" }}>
        ← Back to batches
      </Link>
    </div>
  );
}
