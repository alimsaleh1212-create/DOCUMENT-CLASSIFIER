import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { isLoggedIn, getRole } from "./hooks/useAuth";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import MePage from "./pages/MePage";
import BatchesListPage from "./pages/BatchesListPage";
import BatchDetailPage from "./pages/BatchDetailPage";
import PredictionsRecentPage from "./pages/PredictionsRecentPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AuditPage from "./pages/AuditPage";
import NotFoundPage from "./pages/NotFoundPage";
import ForbiddenPage from "./pages/ForbiddenPage";

// ── Route guards ──────────────────────────────────────────────────────────────

function ProtectedRoute() {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function AdminOnlyRoute() {
  const role = getRole();
  if (role !== "admin") return <ForbiddenPage requiredRole="admin" />;
  return <Outlet />;
}

function AuditRoute() {
  const role = getRole();
  if (role !== "admin" && role !== "auditor") {
    return <ForbiddenPage requiredRole="admin or auditor" />;
  }
  return <Outlet />;
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Authenticated */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/batches" replace />} />
        <Route path="/me" element={<MePage />} />
        <Route path="/batches" element={<BatchesListPage />} />
        <Route path="/batches/:bid" element={<BatchDetailPage />} />
        <Route path="/predictions/recent" element={<PredictionsRecentPage />} />

        {/* Admin only */}
        <Route element={<AdminOnlyRoute />}>
          <Route path="/admin/users" element={<AdminUsersPage />} />
        </Route>

        {/* Admin + Auditor */}
        <Route element={<AuditRoute />}>
          <Route path="/audit" element={<AuditPage />} />
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
