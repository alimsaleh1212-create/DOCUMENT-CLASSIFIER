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

  const { data: users, isLoading, isError } = useQuery<UserOut[]>({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await client.get<UserOut[]>("/users");
      return res.data;
    },
    staleTime: 30_000,
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
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 5 }).map((_, j) => (
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
                <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)", padding: "2.5rem" }}>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
