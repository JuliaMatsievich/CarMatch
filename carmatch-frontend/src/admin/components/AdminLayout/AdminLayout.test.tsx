import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { AdminLayout } from "./AdminLayout";
import { AuthProvider } from "../../../contexts/AuthContext";

const TOKEN_KEY = "carmatch_access_token";
const USER_KEY = "carmatch_user";

function adminUser() {
  return {
    id: 1,
    email: "admin@test.com",
    is_active: true,
    is_admin: true,
    created_at: "2024-01-01T00:00:00Z",
  };
}

describe("AdminLayout", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem(TOKEN_KEY, "admin-token");
    localStorage.setItem(USER_KEY, JSON.stringify(adminUser()));
  });

  it("renders title and subtitle", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <AdminLayout title="Каталог автомобилей" subtitle="Управление каталогом">
            <p>Content</p>
          </AdminLayout>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
        "Каталог автомобилей"
      );
    });
    expect(screen.getByText("Управление каталогом")).toBeInTheDocument();
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("renders nav items", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <AdminLayout title="Страница">
            <div>Body</div>
          </AdminLayout>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByText("Каталог автомобилей")).toBeInTheDocument();
    });
    expect(screen.getByText("Пользователи")).toBeInTheDocument();
  });

  it("shows current user email", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <AdminLayout title="Страница">
            <div>Body</div>
          </AdminLayout>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByText(/admin@test\.com/)).toBeInTheDocument();
    });
  });

  it("renders logout button", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <AdminLayout title="Страница">
            <div>Body</div>
          </AdminLayout>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByRole("button", { name: /выйти/i })).toBeInTheDocument();
    });
  });

  it("logout navigates to /login", async () => {
    let navigateFn: (path: string) => void;
    function CaptureNavigate() {
      const navigate = useNavigate();
      navigateFn = navigate;
      return null;
    }

    render(
      <MemoryRouter>
        <AuthProvider>
          <CaptureNavigate />
          <AdminLayout title="Страница">
            <div>Body</div>
          </AdminLayout>
        </AuthProvider>
      </MemoryRouter>
    );

    await vi.waitFor(() => {
      expect(screen.getByRole("button", { name: /выйти/i })).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /выйти/i }));

    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
