import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  getToken,
  setToken,
  clearToken,
  isLoggedIn,
  getRole,
  getStoredUser,
} from "../hooks/useAuth";

// We don't test the hook (requires React), we test the pure helpers exported from useAuth.ts

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

// ── Token helpers ─────────────────────────────────────────────────────────────

describe("token helpers", () => {
  it("stores and retrieves a token", () => {
    setToken("test-jwt-token");
    expect(getToken()).toBe("test-jwt-token");
  });

  it("clearToken removes the jwt and user keys", () => {
    setToken("test-jwt-token");
    localStorage.setItem("user", JSON.stringify({ id: "1", email: "a@b.com", role: "admin" }));
    clearToken();
    expect(getToken()).toBeNull();
    expect(localStorage.getItem("user")).toBeNull();
  });

  it("isLoggedIn returns false when no token", () => {
    expect(isLoggedIn()).toBe(false);
  });

  it("isLoggedIn returns true after setToken", () => {
    setToken("something");
    expect(isLoggedIn()).toBe(true);
  });
});

// ── Role reading ──────────────────────────────────────────────────────────────

describe("getRole", () => {
  it("returns null when no user stored", () => {
    expect(getRole()).toBeNull();
  });

  it("returns the stored role from localStorage user object", () => {
    setToken("dummy");
    localStorage.setItem("user", JSON.stringify({ id: "1", email: "a@b.com", role: "reviewer" }));
    expect(getRole()).toBe("reviewer");
  });

  it("returns null for a malformed user object", () => {
    setToken("dummy");
    localStorage.setItem("user", "not-json{{{");
    expect(getRole()).toBeNull();
  });
});

// ── getStoredUser ─────────────────────────────────────────────────────────────

describe("getStoredUser", () => {
  it("returns null when nothing is stored", () => {
    expect(getStoredUser()).toBeNull();
  });

  it("returns the parsed user object", () => {
    const u = { id: "abc", email: "test@test.com", role: "auditor" as const };
    localStorage.setItem("user", JSON.stringify(u));
    expect(getStoredUser()).toEqual(u);
  });
});
