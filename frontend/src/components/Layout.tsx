import { Link, useLocation } from "react-router-dom";
import { useAuth, getRole } from "../hooks/useAuth";
import type { Role } from "../api/types";

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const { pathname } = useLocation();
  const active = pathname === to || (to !== "/" && pathname.startsWith(to));
  return (
    <Link
      to={to}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.45rem 0.85rem",
        borderRadius: "var(--radius)",
        fontSize: "15px",
        fontWeight: active ? "600" : "400",
        color: active ? "var(--accent)" : "var(--text-muted)",
        background: active ? "var(--accent-glow)" : "transparent",
        textDecoration: "none",
        transition: "all 0.15s",
        whiteSpace: "nowrap",
      }}
      onMouseEnter={(e) => {
        if (!active) (e.currentTarget as HTMLElement).style.color = "var(--text)";
      }}
      onMouseLeave={(e) => {
        if (!active) (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
      }}
    >
      {children}
    </Link>
  );
}

function RolePill({ role }: { role: Role }) {
  const colors: Record<Role, string> = {
    admin: "var(--role-admin)",
    reviewer: "var(--role-reviewer)",
    auditor: "var(--role-auditor)",
  };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "0.2rem 0.6rem",
        borderRadius: "20px",
        fontSize: "12px",
        fontFamily: "var(--font-mono)",
        fontWeight: "500",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: colors[role],
        background: `${colors[role]}18`,
        border: `1px solid ${colors[role]}30`,
      }}
    >
      {role}
    </span>
  );
}

export function Navbar() {
  const { logout } = useAuth();
  const role = getRole();

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        background: "rgba(6, 8, 15, 0.88)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
        padding: "0 1.75rem",
        height: "58px",
        display: "flex",
        alignItems: "center",
        gap: "2rem",
      }}
    >
      <Link
        to="/batches"
        style={{ display: "flex", alignItems: "center", gap: "0.6rem", textDecoration: "none", flexShrink: 0 }}
      >
        <div
          style={{
            width: "30px", height: "30px",
            background: "var(--accent)",
            borderRadius: "7px",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          <svg width="17" height="17" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="2" width="5" height="6" rx="1" fill="#06080F" />
            <rect x="9" y="2" width="5" height="3" rx="1" fill="#06080F" />
            <rect x="9" y="7" width="5" height="7" rx="1" fill="#06080F" />
            <rect x="2" y="10" width="5" height="4" rx="1" fill="#06080F" />
          </svg>
        </div>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: "700",
            fontSize: "17px",
            color: "#E8F0FF",
            letterSpacing: "-0.02em",
          }}
        >
          DocClass
        </span>
      </Link>

      <nav style={{ display: "flex", alignItems: "center", gap: "0.25rem", flex: 1 }}>
        <NavLink to="/batches">Batches</NavLink>
        <NavLink to="/predictions/recent">Predictions</NavLink>
        {role === "admin" && <NavLink to="/admin/users">Users</NavLink>}
        {(role === "admin" || role === "auditor") && <NavLink to="/audit">Audit</NavLink>}
        <NavLink to="/me">Profile</NavLink>
      </nav>

      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        {role && <RolePill role={role} />}
        <button className="btn btn-ghost btn-sm" onClick={logout}>
          Sign out
        </button>
      </div>
    </header>
  );
}

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function Layout({ children, title, subtitle, actions }: LayoutProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Navbar />
      <main
        style={{
          flex: 1,
          maxWidth: "1200px",
          width: "100%",
          margin: "0 auto",
          padding: "2.25rem 1.75rem",
        }}
      >
        {(title || actions) && (
          <div
            className="animate-fade-up"
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              marginBottom: "2rem",
              gap: "1rem",
            }}
          >
            <div>
              {title && <h1 style={{ fontSize: "26px", marginBottom: "0.3rem" }}>{title}</h1>}
              {subtitle && (
                <p style={{ color: "var(--text-muted)", fontSize: "15px", margin: 0 }}>
                  {subtitle}
                </p>
              )}
            </div>
            {actions && <div style={{ flexShrink: 0 }}>{actions}</div>}
          </div>
        )}
        {children}
      </main>
    </div>
  );
}

export { RolePill };
export type { Role };
