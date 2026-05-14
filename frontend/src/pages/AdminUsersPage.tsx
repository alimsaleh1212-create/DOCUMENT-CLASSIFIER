import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Layout, RolePill } from "../components/Layout";
import { Toast } from "../components/Toast";
import client from "../api/client";
import type { UserOut, Role } from "../api/types";

const ROLES: Role[] = ["admin", "reviewer", "auditor"];

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<UserOut | null>(null);

  const { data: users, isLoading, isError } = useQuery<UserOut[]>({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await client.get<UserOut[]>("/users");
      return res.data;
    },
    staleTime: 30_000,
  });

  const deleteMutation = useMutation({
    mutationFn: async (uid: string) => {
      await client.delete(`/users/${uid}`);
    },
    onSuccess: (_, uid) => {
      queryClient.setQueryData<UserOut[]>(["users"], (old) =>
        old?.filter((u) => u.id !== uid) ?? []
      );
      setToast({ msg: "User deleted.", type: "success" });
      setConfirmDelete(null);
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      const detail = err?.response?.data?.detail ?? "Failed to delete user.";
      setToast({ msg: detail, type: "error" });
      setConfirmDelete(null);
    },
  });

  const roleMutation = useMutation({
    mutationFn: async ({ uid, newRole }: { uid: string; newRole: Role }) => {
      const res = await client.patch<UserOut>(`/users/${uid}/role`, { new_role: newRole });
      return res.data;
    },
    onMutate: async ({ uid, newRole }) => {
      await queryClient.cancelQueries({ queryKey: ["users"] });
      const prev = queryClient.getQueryData<UserOut[]>(["users"]);
      queryClient.setQueryData<UserOut[]>(["users"], (old) =>
        old?.map((u) => (u.id === uid ? { ...u, role: newRole } : u)) ?? []
      );
      return { prev };
    },
    onError: (_err, _vars, context) => {
      queryClient.setQueryData(["users"], context?.prev);
      setToast({ msg: "Failed to update role. Changes reverted.", type: "error" });
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<UserOut[]>(["users"], (old) =>
        old?.map((u) => (u.id === updated.id ? updated : u)) ?? []
      );
      void queryClient.invalidateQueries({ queryKey: ["me"] });
      setToast({ msg: `Role updated to "${updated.role}".`, type: "success" });
    },
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  return (
    <Layout
      title="User Management"
      subtitle="Manage roles and access for all registered users"
    >
      {toast && (
        <Toast message={toast.msg} type={toast.type} onClose={() => setToast(null)} />
      )}

      {/* Delete confirm dialog */}
      {confirmDelete && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 200,
          background: "rgba(6,8,15,0.82)", backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem",
        }}>
          <div className="card animate-fade-up" style={{ maxWidth: "400px", padding: "1.5rem" }}>
            <h3 style={{ margin: "0 0 0.5rem", fontSize: "17px", fontFamily: "var(--font-display)", color: "#E8F0FF" }}>
              Delete user?
            </h3>
            <p style={{ fontSize: "14px", color: "var(--text-muted)", margin: "0 0 1.25rem" }}>
              This will permanently delete <strong style={{ color: "var(--text)" }}>{confirmDelete.email}</strong> and
              remove all their access. This action cannot be undone.
            </p>
            <div style={{ display: "flex", gap: "0.625rem", justifyContent: "flex-end" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => setConfirmDelete(null)}>
                Cancel
              </button>
              <button
                className="btn btn-sm"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(confirmDelete.id)}
                style={{
                  background: "var(--danger)",
                  color: "#fff",
                  fontWeight: "600",
                  opacity: deleteMutation.isPending ? 0.7 : 1,
                }}
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {isError && (
        <div
          style={{
            padding: "1rem",
            background: "rgba(239,68,68,0.06)",
            border: "1px solid rgba(239,68,68,0.2)",
            borderRadius: "var(--radius)",
            color: "var(--danger)",
            fontSize: "15px",
          }}
        >
          Failed to load users.
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Current role</th>
              <th>Status</th>
              <th>Joined</th>
              <th>Change role</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j}>
                      <div
                        className="skeleton"
                        style={{ height: "16px", width: j === 0 ? "180px" : "80px" }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            {!isLoading && users?.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)", padding: "2.5rem" }}>
                  No users found.
                </td>
              </tr>
            )}
            {users?.map((user, idx) => (
              <tr
                key={user.id}
                className="animate-fade-up"
                style={{ animationDelay: `${idx * 40}ms` }}
              >
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
                    <div
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "50%",
                        background: "linear-gradient(135deg, var(--accent), #818CF8)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: "var(--font-display)",
                        fontWeight: "700",
                        fontSize: "13px",
                        color: "#06080F",
                        flexShrink: 0,
                      }}
                    >
                      {user.email[0].toUpperCase()}
                    </div>
                    <span style={{ fontSize: "15px" }}>{user.email}</span>
                  </div>
                </td>
                <td>
                  <RolePill role={user.role} />
                </td>
                <td>
                  <span
                    style={{
                      fontSize: "14px",
                      color: user.is_active ? "var(--success)" : "var(--danger)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {user.is_active ? "active" : "inactive"}
                  </span>
                </td>
                <td style={{ color: "var(--text-muted)", fontSize: "14px" }}>
                  {formatDate(user.created_at)}
                </td>
                <td>
                  <select
                    className="select"
                    value={user.role}
                    disabled={roleMutation.isPending}
                    onChange={(e) =>
                      roleMutation.mutate({ uid: user.id, newRole: e.target.value as Role })
                    }
                    style={{
                      opacity: roleMutation.isPending ? 0.5 : 1,
                    }}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <button
                    title="Delete user"
                    onClick={() => setConfirmDelete(user)}
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      color: "var(--text-dim)", padding: "0.25rem", borderRadius: "4px",
                      display: "flex", alignItems: "center",
                      transition: "color 0.12s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget as HTMLElement).style.color = "var(--danger)"}
                    onMouseLeave={(e) => (e.currentTarget as HTMLElement).style.color = "var(--text-dim)"}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                      <path d="M10 11v6M14 11v6"/>
                      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
                    </svg>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
