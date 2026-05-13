import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import client from "../api/client";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      await client.post("/auth/register", { email, password });
      navigate("/login", {
        state: { registered: true },
        replace: true,
      });
    } catch (err: unknown) {
      if (
        err &&
        typeof err === "object" &&
        "response" in err
      ) {
        const resp = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
        if (resp?.status === 409) {
          setError("An account with that email already exists.");
        } else {
          setError(resp?.data?.detail ?? "Registration failed. Please try again.");
        }
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
        className="animate-fade-up"
        style={{ width: "100%", maxWidth: "380px", position: "relative" }}
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
              Create account
            </h1>
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "12px",
                fontFamily: "var(--font-mono)",
                letterSpacing: "0.04em",
                margin: 0,
              }}
            >
              New accounts start as{" "}
              <span
                style={{
                  color: "var(--role-reviewer)",
                  background: "rgba(56,189,248,0.1)",
                  padding: "0 5px",
                  borderRadius: "3px",
                  fontWeight: "500",
                }}
              >
                reviewer
              </span>
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
                htmlFor="reg-email"
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
                id="reg-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="input"
              />
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label
                htmlFor="reg-password"
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
                id="reg-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 8 characters"
                className="input"
              />
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <label
                htmlFor="reg-confirm"
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
                Confirm password
              </label>
              <input
                id="reg-confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Repeat password"
                className="input"
                style={{
                  borderColor:
                    confirm && confirm !== password
                      ? "var(--danger)"
                      : undefined,
                }}
              />
              {confirm && confirm !== password && (
                <p
                  style={{
                    fontSize: "11px",
                    color: "var(--danger)",
                    margin: "0.3rem 0 0",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  Passwords don't match
                </p>
              )}
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
              disabled={loading || (!!confirm && confirm !== password)}
              style={{ width: "100%", justifyContent: "center", height: "38px" }}
            >
              {loading ? (
                <span className="spinner" style={{ width: "16px", height: "16px" }} />
              ) : (
                "Create account"
              )}
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
              Already have an account?{" "}
              <Link
                to="/login"
                style={{ color: "var(--accent)", textDecoration: "none" }}
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>

        {/* Role info */}
        <div
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1rem",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius)",
            fontSize: "11px",
            color: "var(--text-dim)",
            fontFamily: "var(--font-mono)",
            lineHeight: "1.6",
          }}
        >
          <div style={{ color: "var(--text-muted)", marginBottom: "0.4rem", fontWeight: "500" }}>
            Role privileges
          </div>
          <div>
            <span style={{ color: "var(--role-admin)" }}>admin</span>
            {"  →  "}manage users, view all, relabel, audit
          </div>
          <div>
            <span style={{ color: "var(--role-reviewer)" }}>reviewer</span>
            {" →  "}view batches + relabel predictions
          </div>
          <div>
            <span style={{ color: "var(--role-auditor)" }}>auditor</span>
            {"  →  "}view batches + audit log (read-only)
          </div>
        </div>

        <p
          style={{
            textAlign: "center",
            fontSize: "11px",
            color: "var(--text-dim)",
            fontFamily: "var(--font-mono)",
            marginTop: "1rem",
          }}
        >
          RVL-CDIP · 16-class classifier
        </p>
      </div>
    </div>
  );
}
