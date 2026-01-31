import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./AuthContext";

function TestConsumer() {
  const { token, user, login, register, logout } = useAuth();
  return (
    <div>
      <span data-testid="token">{token ?? "null"}</span>
      <span data-testid="user">{user ? user.email : "null"}</span>
      <button
        type="button"
        onClick={() =>
          login("tok123", {
            id: 1,
            email: "a@b.com",
            is_active: true,
            created_at: "2024-01-01",
          })
        }
      >
        Login
      </button>
      <button
        type="button"
        onClick={() =>
          register("tok456", {
            id: 2,
            email: "c@d.com",
            is_active: true,
            created_at: "2024-01-02",
          })
        }
      >
        Register
      </button>
      <button type="button" onClick={logout}>
        Logout
      </button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("throws when useAuth used outside AuthProvider", () => {
    expect(() => render(<TestConsumer />)).toThrow(
      "useAuth must be used within AuthProvider"
    );
  });

  it("provides initial state from localStorage", async () => {
    localStorage.setItem("carmatch_access_token", "stored-token");
    localStorage.setItem(
      "carmatch_user",
      JSON.stringify({
        id: 1,
        email: "stored@test.com",
        is_active: true,
        created_at: "2024-01-01",
      })
    );

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await vi.waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("stored-token");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("stored@test.com");
  });

  it("login updates state and localStorage", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await vi.waitFor(() => {
      expect(screen.getByTestId("token")).toHaveTextContent("null");
    });

    await user.click(screen.getByRole("button", { name: /^login$/i }));

    expect(screen.getByTestId("token")).toHaveTextContent("tok123");
    expect(screen.getByTestId("user")).toHaveTextContent("a@b.com");
    expect(localStorage.getItem("carmatch_access_token")).toBe("tok123");
  });

  it("register updates state and localStorage", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: /^register$/i }));

    expect(screen.getByTestId("token")).toHaveTextContent("tok456");
    expect(screen.getByTestId("user")).toHaveTextContent("c@d.com");
  });

  it("logout clears state and localStorage", async () => {
    const user = userEvent.setup();

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: /^login$/i }));
    expect(screen.getByTestId("token")).toHaveTextContent("tok123");

    await user.click(screen.getByRole("button", { name: /^logout$/i }));

    expect(screen.getByTestId("token")).toHaveTextContent("null");
    expect(screen.getByTestId("user")).toHaveTextContent("null");
    expect(localStorage.getItem("carmatch_access_token")).toBeNull();
  });
});
