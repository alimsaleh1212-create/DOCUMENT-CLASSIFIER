import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/batches", { replace: true });
    } catch (err: unknown) {
      if (
        err &&
        typeof err === "object" &&
        "response" in err &&
        (err as { response?: { status?: number } }).response?.status === 401
      ) {
        setError("Invalid credentials. Check your email and password.");
      } else {
        setError("Unable to connect. Make sure the server is running.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background decoration */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 60% 40% at 50% 30%, rgba(34,211,238,0.06) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div
        aria-hidden
        style={{
          position: "absolute",
          top: "15%",
          left: "50%",
          transform: "translateX(-50%)",
          width: "1px",
          height: "200px",
          background:
            "linear-gradient(to bottom, transparent, var(--accent), transparent)",
          opacity: 0.25,
          pointerEvents: "none",
        }}
      />

      {/* Login card */}
      <div
        className="animate-fade-up"
        style={{
          width: "100%",
          maxWidth: "380px",
          position: "relative",
        }}
      >
        {/* Logo mark */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            marginBottom: "2rem",
            gap: "0.75rem",
          }}
        >
          <div
            style={{
              width: "44px",
              height: "44px",
              background: "var(--accent)",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 32px var(--accent-glow)",
            }}
          >
            <svg width="22" height="22" viewBox="0 0 16 16" fill="none">
              <rect x="2" y="2" width="5" height="6" rx="1" fill="#06080F" />
              <rect x="9" y="2" width="5" height="3" rx="1" fill="#06080F" />
              <rect x="9" y="7" width="5" height="7" rx="1" fill="#06080F" />
              <rect x="2" y="10" width="5" height="4" rx="1" fill="#06080F" />
            </svg>
          </div>
          <div style={{ textAlign: "center" }}>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "24px",
                fontWeight: "800",
                color: "#E8F0FF",
                letterSpacing: "-0.03em",
                marginBottom: "0.25rem",
              }}
            >
              DocClass
            </h1>
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "12px",
                fontFamily: "var(--font-mono)",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                margin: 0,
              }}
            >
              Document Intelligence Platform
            </p>
          </div>
        </div>

        {/* Form card */}
        <div
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "12px",
            padding: "1.75rem",
            boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
          }}
        >
          <form onSubmit={(e) => void handleSubmit(e)}>
            <div style={{ marginBottom: "1rem" }}>
              <label
                htmlFor="email"
                style={{
                  display: "block",
                  fontSize: "12px",
                  fontWeight: "500",
                  color: "var(--text-muted)",
                  marginBottom: "0.375rem",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                }}
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="input"
              />
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <label
                htmlFor="password"
                style={{
                  display: "block",
                  fontSize: "12px",
                  fontWeight: "500",
                  color: "var(--text-muted)",
                  marginBottom: "0.375rem",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                }}
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="input"
              />
            </div>

            {error && (
              <div
                role="alert"
                style={{
                  padding: "0.625rem 0.875rem",
                  background: "rgba(239,68,68,0.08)",
                  border: "1px solid rgba(239,68,68,0.2)",
                  borderRadius: "var(--radius)",
                  color: "var(--danger)",
                  fontSize: "12px",
                  marginBottom: "1rem",
                  lineHeight: "1.5",
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: "100%", justifyContent: "center", height: "38px" }}
            >
              {loading ? <span className="spinner" style={{ width: "16px", height: "16px" }} /> : "Sign in"}
            </button>
          </form>

          <div
            style={{
              marginTop: "1.25rem",
              paddingTop: "1rem",
              borderTop: "1px solid var(--border-subtle)",
              textAlign: "center",
            }}
          >
            <p style={{ fontSize: "12px", color: "var(--text-dim)", margin: 0 }}>
              No account?{" "}
              <a
                href="/auth/register"
                style={{ color: "var(--accent)", textDecoration: "none" }}
              >
                Contact your admin
              </a>
            </p>
          </div>
        </div>

        {/* Version footer */}
        <p
          style={{
            textAlign: "center",
            fontSize: "11px",
            color: "var(--text-dim)",
            fontFamily: "var(--font-mono)",
            marginTop: "1.25rem",
          }}
        >
          RVL-CDIP · 16-class classifier
        </p>
      </div>
    </div>
  );
}
