import { useNavigate } from "react-router-dom";
import client from "../api/client";
import type { LoginResponse, Role } from "../api/types";

const JWT_KEY = "jwt";
const USER_KEY = "user";

export interface StoredUser {
  id: string;
  email: string;
  role: Role;
}

// ── Token helpers (exported for tests) ───────────────────────────────────────

export function getToken(): string | null {
  return localStorage.getItem(JWT_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(JWT_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(JWT_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function getStoredUser(): StoredUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

export function getRole(): Role | null {
  return getStoredUser()?.role ?? null;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth() {
  const navigate = useNavigate();

  async function login(email: string, password: string): Promise<void> {
    const response = await client.post<LoginResponse>("/auth/jwt/login", {
      email,
      password,
    });
    setToken(response.data.access_token);
    const user: StoredUser = {
      id: response.data.id,
      email: response.data.email,
      role: response.data.role,
    };
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function logout(): void {
    clearToken();
    navigate("/login");
  }

  return {
    login,
    logout,
    isLoggedIn: isLoggedIn(),
    role: getRole(),
    user: getStoredUser(),
  };
}
