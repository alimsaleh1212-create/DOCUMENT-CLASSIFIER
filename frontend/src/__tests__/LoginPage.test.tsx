import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LoginPage from "../pages/LoginPage";
import client from "../api/client";

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderLoginPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <QueryClientProvider client={queryClient}>
        <LoginPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("LoginPage", () => {
  it("renders email and password fields", () => {
    renderLoginPage();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("shows sign-in button", () => {
    renderLoginPage();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("stores token and navigates away on successful login", async () => {
    const user = userEvent.setup();
    vi.spyOn(client, "post").mockResolvedValueOnce({
      data: {
        access_token: "test-token",
        token_type: "bearer",
        id: "u1",
        email: "admin@test.com",
        role: "admin",
        is_active: true,
        created_at: new Date().toISOString(),
      },
    } as never);

    renderLoginPage();

    await user.type(screen.getByLabelText(/email/i), "admin@test.com");
    await user.type(screen.getByLabelText(/password/i), "password123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(localStorage.getItem("jwt")).toBe("test-token");
    });
  });

  it("shows inline error on 401 response", async () => {
    const user = userEvent.setup();
    const axiosError = {
      isAxiosError: true,
      response: { status: 401, data: { detail: "Invalid credentials" } },
    };
    vi.spyOn(client, "post").mockRejectedValueOnce(axiosError);

    renderLoginPage();

    await user.type(screen.getByLabelText(/email/i), "bad@test.com");
    await user.type(screen.getByLabelText(/password/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/invalid credentials/i);
    });
    expect(localStorage.getItem("jwt")).toBeNull();
  });
});
