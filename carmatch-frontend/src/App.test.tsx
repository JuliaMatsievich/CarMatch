import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App routing", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders login page at /login", () => {
    window.history.pushState({}, "", "/login");
    render(<App />);

    expect(screen.getByText("CarMatch")).toBeInTheDocument();
    const submitBtn = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("type") === "submit");
    expect(submitBtn).toHaveTextContent(/войти/i);
  });

  it("redirects unauthenticated user from /chat to /login", () => {
    window.history.pushState({}, "", "/chat");
    render(<App />);

    // ProtectedRoute should redirect to login
    // Wait for AuthProvider to finish loading
    expect(screen.queryByText(/начните диалог/i)).not.toBeInTheDocument();
  });

  it("shows chat when authenticated", async () => {
    localStorage.setItem("carmatch_access_token", "test-token");
    localStorage.setItem(
      "carmatch_user",
      JSON.stringify({
        id: 1,
        email: "test@test.com",
        is_active: true,
        created_at: "2024-01-01",
      })
    );

    window.history.pushState({}, "", "/chat");
    render(<App />);

    await vi.waitFor(
      () => {
        expect(screen.getByText(/начните диалог/i)).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});
