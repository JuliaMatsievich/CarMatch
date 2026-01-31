import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import AuthPage from "./AuthPage";
import { AuthProvider } from "../contexts/AuthContext";
import * as authApi from "../api/auth";
import type { AuthResponse } from "../api/auth";

vi.mock("../api/auth");

function renderAuthPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <AuthPage />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("AuthPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form by default", () => {
    renderAuthPage();

    expect(screen.getByText("CarMatch")).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/пароль/i)).toBeInTheDocument();
    const submitBtn = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("type") === "submit");
    expect(submitBtn).toHaveTextContent(/войти/i);
  });

  it("toggles between login and register", async () => {
    const user = userEvent.setup();
    renderAuthPage();

    await user.click(screen.getByRole("button", { name: /регистрация/i }));

    const submitBtn = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("type") === "submit");
    expect(submitBtn).toHaveTextContent(/зарегистрироваться/i);
  });

  it("submits login form and navigates on success", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "token123",
      token_type: "bearer",
      user: {
        id: 1,
        email: "test@test.com",
        is_active: true,
        created_at: "2024-01-01",
      },
    });

    renderAuthPage();

    await user.type(screen.getByLabelText(/email/i), "test@test.com");
    await user.type(screen.getByLabelText(/пароль/i), "password123");
    const submitBtn = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("type") === "submit");
    await user.click(submitBtn!);

    expect(authApi.login).toHaveBeenCalledWith("test@test.com", "password123");
  });

  it("shows error on login failure", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockRejectedValue({
      response: { data: { detail: "Invalid credentials" } },
    });

    renderAuthPage();

    await user.type(screen.getByLabelText(/email/i), "bad@test.com");
    await user.type(screen.getByLabelText(/пароль/i), "wrongpass");
    const submitBtn = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("type") === "submit");
    await user.click(submitBtn!);

    await vi.waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  it("shows validation error from array detail", async () => {
    const user = userEvent.setup();
    vi.mocked(authApi.login).mockRejectedValue({
      response: {
        data: {
          detail: [{ msg: "Password too short" }],
        },
      },
    });

    renderAuthPage();

    await user.type(screen.getByLabelText(/email/i), "a@b.com");
    await user.type(screen.getByLabelText(/пароль/i), "short");
    const submitBtn = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("type") === "submit");
    await user.click(submitBtn!);

    await vi.waitFor(() => {
      expect(screen.getByText("Password too short")).toBeInTheDocument();
    });
  });

  it("disables submit during loading", async () => {
    const user = userEvent.setup();
    let resolveLogin!: (value: AuthResponse) => void;
    vi.mocked(authApi.login).mockImplementation(
      () =>
        new Promise<AuthResponse>((r) => {
          resolveLogin = r;
        })
    );

    renderAuthPage();

    await user.type(screen.getByLabelText(/email/i), "a@b.com");
    await user.type(screen.getByLabelText(/пароль/i), "password123");
    const submitBtn = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("type") === "submit");
    await user.click(submitBtn!);

    expect(screen.getByRole("button", { name: /загрузка/i })).toBeDisabled();

    resolveLogin({
      access_token: "t",
      token_type: "bearer",
      user: {
        id: 1,
        email: "a@b.com",
        is_active: true,
        created_at: "2024-01-01",
      },
    });
  });
});
