import { useQuery } from "@tanstack/react-query";
import { Layout, RolePill } from "../components/Layout";
import { useAuth } from "../hooks/useAuth";
import client from "../api/client";
import type { UserOut } from "../api/types";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.3rem",
        padding: "1rem 1.25rem",
        background: "var(--bg-raised)",
        borderRadius: "var(--radius)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <span
        style={{
          fontSize: "12px",
          fontFamily: "var(--font-mono)",
          fontWeight: "500",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: "var(--text-dim)",
        }}
      >
        {label}
      </span>
      <span style={{ color: "var(--text)", fontSize: "16px" }}>{value}</span>
    </div>
  );
}

export default function MePage() {
  const { logout } = useAuth();
  const {
    data: user,
    isLoading,
    isError,
  } = useQuery<UserOut>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await client.get<UserOut>("/me");
      return res.data;
    },
    staleTime: 60_000,
  });

  return (
    <Layout title="My Profile">
      {isLoading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ height: "64px", width: "100%" }} />
          ))}
        </div>
      )}

      {isError && (
        <div
          style={{
            padding: "1.5rem",
            background: "rgba(239,68,68,0.06)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "var(--radius)",
            color: "var(--danger)",
            fontSize: "15px",
          }}
        >
          Failed to load profile.
        </div>
      )}

      {user && (
        <div className="animate-fade-up" style={{ maxWidth: "480px" }}>
          {/* Avatar area */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "1rem",
              marginBottom: "1.5rem",
              padding: "1.25rem",
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                background: "linear-gradient(135deg, var(--accent), #818CF8)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-display)",
                fontWeight: "700",
                fontSize: "20px",
                color: "#06080F",
                flexShrink: 0,
              }}
            >
              {user.email[0].toUpperCase()}
            </div>
            <div>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: "700",
                  fontSize: "18px",
                  color: "#E8F0FF",
                  marginBottom: "0.25rem",
                }}
              >
                {user.email}
              </div>
              <RolePill role={user.role} />
            </div>
          </div>

          {/* Fields */}
          <div
            className="stagger"
            style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
          >
            <div className="animate-fade-up">
              <Field label="User ID" value={<code className="mono" style={{ fontSize: "14px", color: "var(--text-muted)" }}>{user.id}</code>} />
            </div>
            <div className="animate-fade-up">
              <Field label="Email" value={user.email} />
            </div>
            <div className="animate-fade-up">
              <Field
                label="Role"
                value={<RolePill role={user.role} />}
              />
            </div>
            <div className="animate-fade-up">
              <Field
                label="Status"
                value={
                  <span style={{ color: user.is_active ? "var(--success)" : "var(--danger)" }}>
                    {user.is_active ? "● Active" : "● Inactive"}
                  </span>
                }
              />
            </div>
            <div className="animate-fade-up">
              <Field
                label="Member since"
                value={new Date(user.created_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              />
            </div>
          </div>

          <button
            className="btn btn-danger"
            onClick={logout}
            style={{ marginTop: "1.5rem" }}
          >
            Sign out
          </button>
        </div>
      )}
    </Layout>
  );
}
