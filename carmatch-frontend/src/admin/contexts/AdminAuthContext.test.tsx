import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  AdminAuthProvider,
  useAdminAuth,
} from "./AdminAuthContext";

const ADMIN_TOKEN_KEY = "carmatch_admin_access_token";
const ADMIN_USER_KEY = "carmatch_admin_user";

function adminUser(overrides?: { is_admin?: boolean }) {
  return {
    id: 1,
    email: "admin@test.com",
    is_active: true,
    is_admin: true,
    created_at: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

function TestConsumer() {
  const { token, user, login, logout } = useAdminAuth();
  return (
    <div>
      <span data-testid="token">{token ?? "null"}</span>
      <span data-testid="user">{user ? user.email : "null"}</span>
      <button
        type="button"
        onClick={() => login("admin-tok", adminUser())}
      >
        Admin Login
      </button>
      <button type="button" onClick={logout}>
        Logout
      </button>
    </div>
  );
}

describe("AdminAuthContext", () => {
  beforeEach(() => {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_USER_KEY);
    vi.clearAllMocks();
  });

  it("throws when useAdminAuth is used outside AdminAuthProvider", () => {
    expect(() => render(<TestConsumer />)).toThrow(
      "useAdminAuth must be used within AdminAuthProvider"
    );
  });

  it("restores state from localStorage on mount", async () => {
    localStorage.setItem(ADMIN_TOKEN_KEY, "stored-admin-token");
    localStorage.setItem(
      ADMIN_USER_KEY,
      JSON.stringify(adminUser())
    );

    render(
      <AdminAuthProvider>
        <TestConsumer />
      </AdminAuthProvider>
    );

    await vi.waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("stored-admin-token");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("admin@test.com");
  });

  it("does not restore state when user is not admin", async () => {
    localStorage.setItem(ADMIN_TOKEN_KEY, "token");
    localStorage.setItem(
      ADMIN_USER_KEY,
      JSON.stringify(adminUser({ is_admin: false }))
    );

    render(
      <AdminAuthProvider>
        <TestConsumer />
      </AdminAuthProvider>
    );

    await vi.waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("null");
      expect(screen.getByTestId("user")).toHaveTextContent("null");
    });
  });

  it("login updates state and localStorage", async () => {
    const user = userEvent.setup();

    render(
      <AdminAuthProvider>
        <TestConsumer />
      </AdminAuthProvider>
    );

    await vi.waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("null");
    });

    await user.click(screen.getByRole("button", { name: /admin login/i }));

    expect(screen.getByTestId("token")).toHaveTextContent("admin-tok");
    expect(screen.getByTestId("user")).toHaveTextContent("admin@test.com");
    expect(localStorage.getItem(ADMIN_TOKEN_KEY)).toBe("admin-tok");
  });

  it("login does not update state when user is not admin", async () => {
    function BadConsumer() {
      const { token, login } = useAdminAuth();
      const [err, setErr] = React.useState<string | null>(null);
      return (
        <div>
          <span data-testid="token">{token ?? "null"}</span>
          <button
            type="button"
            onClick={() => {
              try {
                login("t", adminUser({ is_admin: false }));
              } catch (e) {
                setErr(e instanceof Error ? e.message : "error");
              }
            }}
          >
            Bad Login
          </button>
          {err && <span data-testid="error">{err}</span>}
        </div>
      );
    }

    const user = userEvent.setup();
    render(
      <AdminAuthProvider>
        <BadConsumer />
      </AdminAuthProvider>
    );

    await vi.waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("null");
    });

    await user.click(screen.getByRole("button", { name: /bad login/i }));

    expect(screen.getByTestId("error")).toHaveTextContent(
      "Пользователь не является администратором"
    );
    expect(screen.getByTestId("token")).toHaveTextContent("null");
  });

  it("logout clears state and localStorage", async () => {
    const user = userEvent.setup();

    render(
      <AdminAuthProvider>
        <TestConsumer />
      </AdminAuthProvider>
    );

    await user.click(screen.getByRole("button", { name: /admin login/i }));
    expect(screen.getByTestId("token")).toHaveTextContent("admin-tok");

    await user.click(screen.getByRole("button", { name: /^logout$/i }));

    expect(screen.getByTestId("token")).toHaveTextContent("null");
    expect(screen.getByTestId("user")).toHaveTextContent("null");
    expect(localStorage.getItem(ADMIN_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(ADMIN_USER_KEY)).toBeNull();
  });
});
