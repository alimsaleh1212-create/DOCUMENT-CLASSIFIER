import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminUsersPage from "../pages/AdminUsersPage";
import client from "../api/client";
import type { UserOut } from "../api/types";

// ── Fixture data ──────────────────────────────────────────────────────────────

const USERS: UserOut[] = [
  {
    id: "u1",
    email: "admin@test.com",
    role: "admin",
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "u2",
    email: "reviewer@test.com",
    role: "reviewer",
    is_active: true,
    created_at: new Date().toISOString(),
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderAdminUsersPage() {
  // Seed localStorage so Layout's RolePill works
  localStorage.setItem("jwt", "dummy-jwt");
  localStorage.setItem("user", JSON.stringify({ id: "u1", email: "admin@test.com", role: "admin" }));

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return { queryClient, ...render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <AdminUsersPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )};
}

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("AdminUsersPage", () => {
  it("renders a row for each user", async () => {
    vi.spyOn(client, "get").mockResolvedValueOnce({ data: USERS } as never);

    renderAdminUsersPage();

    await waitFor(() => {
      expect(screen.getByText("admin@test.com")).toBeInTheDocument();
      expect(screen.getByText("reviewer@test.com")).toBeInTheDocument();
    });
  });

  it("calls PATCH when role dropdown changes", async () => {
    const user = userEvent.setup();
    vi.spyOn(client, "get").mockResolvedValueOnce({ data: USERS } as never);
    const patchSpy = vi.spyOn(client, "patch").mockResolvedValueOnce({
      data: { ...USERS[1], role: "auditor" },
    } as never);

    renderAdminUsersPage();

    await waitFor(() => screen.getByText("reviewer@test.com"));

    // Find the select in the second user's row
    const rows = screen.getAllByRole("row");
    const reviewerRow = rows.find((r) => within(r).queryByText("reviewer@test.com"));
    expect(reviewerRow).toBeDefined();

    const select = within(reviewerRow!).getByRole("combobox");
    await user.selectOptions(select, "auditor");

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledWith(
        "/users/u2/role",
        { new_role: "auditor" },
      );
    });
  });

  it("shows optimistic update before server reply settles", async () => {
    const user = userEvent.setup();
    vi.spyOn(client, "get").mockResolvedValueOnce({ data: USERS } as never);

    // Slow PATCH — won't resolve during the test
    vi.spyOn(client, "patch").mockImplementationOnce(
      () => new Promise(() => {}),
    );

    renderAdminUsersPage();
    await waitFor(() => screen.getByText("reviewer@test.com"));

    const rows = screen.getAllByRole("row");
    const reviewerRow = rows.find((r) => within(r).queryByText("reviewer@test.com"));
    const select = within(reviewerRow!).getByRole("combobox") as HTMLSelectElement;

    await user.selectOptions(select, "auditor");

    // Optimistic: the combobox should immediately reflect "auditor"
    await waitFor(() => {
      expect(select.value).toBe("auditor");
    });
  });

  it("reverts to original role on PATCH error", async () => {
    const user = userEvent.setup();
    vi.spyOn(client, "get").mockResolvedValueOnce({ data: USERS } as never);
    vi.spyOn(client, "patch").mockRejectedValueOnce(new Error("Server error"));

    renderAdminUsersPage();
    await waitFor(() => screen.getByText("reviewer@test.com"));

    const rows = screen.getAllByRole("row");
    const reviewerRow = rows.find((r) => within(r).queryByText("reviewer@test.com"));
    const select = within(reviewerRow!).getByRole("combobox") as HTMLSelectElement;

    await user.selectOptions(select, "auditor");

    // After error, role should revert to "reviewer"
    await waitFor(() => {
      expect(select.value).toBe("reviewer");
    });
  });
});
