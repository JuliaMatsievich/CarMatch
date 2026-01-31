import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageInput } from "./MessageInput";

describe("MessageInput", () => {
  it("renders input and submit button", () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    expect(
      screen.getByPlaceholderText("Напишите сообщение...")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /отправить/i })
    ).toBeInTheDocument();
  });

  it("calls onSend with trimmed content on submit", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    const input = screen.getByPlaceholderText("Напишите сообщение...");
    await user.type(input, "  Тестовое сообщение  ");
    await user.click(screen.getByRole("button", { name: /отправить/i }));

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith("Тестовое сообщение");
  });

  it("clears input after submit", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    const input = screen.getByPlaceholderText(
      "Напишите сообщение..."
    ) as HTMLInputElement;
    await user.type(input, "Сообщение");
    await user.click(screen.getByRole("button", { name: /отправить/i }));

    expect(input.value).toBe("");
  });

  it("does not call onSend when input is empty", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    await user.click(screen.getByRole("button", { name: /отправить/i }));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not call onSend when disabled", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} disabled />);

    const input = screen.getByPlaceholderText("Напишите сообщение...");
    await user.type(input, "Сообщение");
    await user.click(screen.getByRole("button", { name: /отправить/i }));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("submit button is disabled when input is empty", () => {
    const onSend = vi.fn();
    render(<MessageInput onSend={onSend} />);

    expect(screen.getByRole("button", { name: /отправить/i })).toBeDisabled();
  });
});
