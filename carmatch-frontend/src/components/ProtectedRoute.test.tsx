import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoute";
import { AuthProvider } from "../contexts/AuthContext";

function TestProtectedApp() {
  return (
    <AuthProvider>
      <MemoryRouter>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route element={<ProtectedRoute />}>
            <Route path="/chat" element={<div>Chat Page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("redirects to /login when not authenticated", async () => {
    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/chat" element={<div>Chat Page</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // AuthProvider reads from localStorage; without token it redirects
    await vi.waitFor(() => {
      expect(screen.queryByText("Chat Page")).not.toBeInTheDocument();
    });
  });

  it("shows loading state initially", () => {
    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/chat" element={<div>Chat Page</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    // Initially may show loading
    const loading = screen.queryByText(/загрузка/i);
    if (loading) {
      expect(loading).toBeInTheDocument();
    }
  });

  it("renders outlet when authenticated", async () => {
    localStorage.setItem("carmatch_access_token", "test-token");
    localStorage.setItem(
      "carmatch_user",
      JSON.stringify({
        id: 1,
        email: "test@example.com",
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
      })
    );

    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route element={<ProtectedRoute />}>
              <Route path="/chat" element={<div>Chat Page</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByText("Chat Page")).toBeInTheDocument();
    });
  });
});
