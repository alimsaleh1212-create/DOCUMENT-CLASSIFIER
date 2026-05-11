import { Routes, Route, Navigate } from "react-router-dom";

function LoginPage() {
  return <div>Login</div>;
}

function MePage() {
  return <div>Profile</div>;
}

function BatchesListPage() {
  return <div>Batches</div>;
}

function BatchDetailPage() {
  return <div>Batch Detail</div>;
}

function AdminUsersPage() {
  return <div>Admin Users</div>;
}

function AuditPage() {
  return <div>Audit Log</div>;
}

function NotFoundPage() {
  return <div>404 Not Found</div>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/me" element={<MePage />} />
      <Route path="/batches" element={<BatchesListPage />} />
      <Route path="/batches/:bid" element={<BatchDetailPage />} />
      <Route path="/admin/users" element={<AdminUsersPage />} />
      <Route path="/audit" element={<AuditPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}