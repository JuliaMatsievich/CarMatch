import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import AdminLoginPage from "./AdminLoginPage";
import { AdminAuthProvider } from "../contexts/AdminAuthContext";
import * as authApi from "../../api/auth";

vi.mock("../../api/auth");

function renderAdminLoginPage() {
  return render(
    <MemoryRouter>
      <AdminAuthProvider>
        <AdminLoginPage />
      </AdminAuthProvider>
    </MemoryRouter>
  );
}

describe("AdminLoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form with default credentials hint", () => {
    renderAdminLoginPage();

    expect(screen.getByText("CarMatch Admin")).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/пароль/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /войти в админ-панель/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/admin@mail\.ru \/ admin1234/)).toBeInTheDocument();
  });

  it("shows error when user is not admin", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token",
      token_type: "bearer",
      user: {
        id: 1,
        email: "user@test.com",
        is_active: true,
        is_admin: false,
        created_at: "2024-01-01",
      },
    });

    renderAdminLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/пароль/i);
    await user.clear(emailInput);
    await user.type(emailInput, "user@test.com");
    await user.clear(passwordInput);
    await user.type(passwordInput, "pass");
    await user.click(
      screen.getByRole("button", { name: /войти в админ-панель/i })
    );

    expect(
      await screen.findByText(/не является администратором/i)
    ).toBeInTheDocument();
  });

  it("shows API error on login failure", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockRejectedValue({
      response: { data: { detail: "Invalid credentials" } },
    });

    renderAdminLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/пароль/i);
    await user.clear(emailInput);
    await user.type(emailInput, "bad@test.com");
    await user.clear(passwordInput);
    await user.type(passwordInput, "wrong");
    await user.click(
      screen.getByRole("button", { name: /войти в админ-панель/i })
    );

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });

  it("shows generic error when API error has no detail", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockRejectedValue(new Error("Network error"));

    renderAdminLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/пароль/i);
    await user.clear(emailInput);
    await user.type(emailInput, "a@b.com");
    await user.clear(passwordInput);
    await user.type(passwordInput, "pass");
    await user.click(
      screen.getByRole("button", { name: /войти в админ-панель/i })
    );

    expect(
      await screen.findByText(/не удалось войти в админ-панель/i)
    ).toBeInTheDocument();
  });

  it("disables submit and shows loading text during submit", async () => {
    const user = userEvent.setup();
    let resolveLogin!: (v: Awaited<ReturnType<typeof authApi.login>>) => void;
    vi.mocked(authApi.login).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve;
        })
    );

    renderAdminLoginPage();

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/пароль/i);
    await user.clear(emailInput);
    await user.type(emailInput, "admin@mail.ru");
    await user.clear(passwordInput);
    await user.type(passwordInput, "admin1234");
    await user.click(
      screen.getByRole("button", { name: /войти в админ-панель/i })
    );

    const loadingButton = await screen.findByRole("button", {
      name: /входим/i,
    });
    expect(loadingButton).toBeDisabled();

    resolveLogin({
      access_token: "t",
      token_type: "bearer",
      user: {
        id: 1,
        email: "admin@mail.ru",
        is_active: true,
        is_admin: true,
        created_at: "2024-01-01",
      },
    });
  });
});
