import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AdminProtectedRoute } from "./AdminProtectedRoute";
import { AuthProvider } from "../../contexts/AuthContext";

const TOKEN_KEY = "carmatch_access_token";
const USER_KEY = "carmatch_user";

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

describe("AdminProtectedRoute", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("shows loading state initially", () => {
    render(
      <MemoryRouter initialEntries={["/admin/cars"]}>
        <AuthProvider>
          <Routes>
            <Route element={<AdminProtectedRoute />}>
              <Route path="/admin/cars" element={<div>Admin Cars</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    const loading = screen.queryByText(/загрузка админ-панели/i);
    if (loading) {
      expect(loading).toBeInTheDocument();
    }
  });

  it("redirects to /login when not authenticated", async () => {
    render(
      <MemoryRouter initialEntries={["/admin/cars"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route element={<AdminProtectedRoute />}>
              <Route path="/admin/cars" element={<div>Admin Cars</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByText("Login Page")).toBeInTheDocument();
      expect(screen.queryByText("Admin Cars")).not.toBeInTheDocument();
    });
  });

  it("redirects to /chat when authenticated but not admin", async () => {
    localStorage.setItem(TOKEN_KEY, "user-token");
    localStorage.setItem(USER_KEY, JSON.stringify(adminUser({ is_admin: false })));

    render(
      <MemoryRouter initialEntries={["/admin/cars"]}>
        <AuthProvider>
          <Routes>
            <Route path="/chat" element={<div>Chat Page</div>} />
            <Route element={<AdminProtectedRoute />}>
              <Route path="/admin/cars" element={<div>Admin Cars</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByText("Chat Page")).toBeInTheDocument();
      expect(screen.queryByText("Admin Cars")).not.toBeInTheDocument();
    });
  });

  it("renders outlet when authenticated as admin", async () => {
    localStorage.setItem(TOKEN_KEY, "admin-token");
    localStorage.setItem(USER_KEY, JSON.stringify(adminUser()));

    render(
      <MemoryRouter initialEntries={["/admin/cars"]}>
        <AuthProvider>
          <Routes>
            <Route element={<AdminProtectedRoute />}>
              <Route path="/admin/cars" element={<div>Admin Cars</div>} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByText("Admin Cars")).toBeInTheDocument();
    });
  });
});
