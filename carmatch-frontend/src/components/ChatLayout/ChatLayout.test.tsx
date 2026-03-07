import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatLayout } from "./ChatLayout";
import type { ChatSessionListItem, MessageListItem } from "../../api/chat";

describe("ChatLayout", () => {
  const defaultProps = {
    sessionId: "s1" as string | null,
    sessions: [] as ChatSessionListItem[],
    messages: [] as MessageListItem[],
    onNewChat: vi.fn(),
    onSelectSession: vi.fn(),
    onSend: vi.fn(),
    onLogout: vi.fn(),
    sendLoading: false,
    userEmail: "user@test.com",
  };

  it("renders sidebar with new chat and logout", () => {
    render(<ChatLayout {...defaultProps} />);

    expect(
      screen.getByRole("button", { name: /новый диалог/i })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /выйти/i })).toBeInTheDocument();
  });

  it("renders message input", () => {
    render(<ChatLayout {...defaultProps} />);

    expect(
      screen.getByPlaceholderText("Напишите сообщение...")
    ).toBeInTheDocument();
  });

  it("renders empty message state when no messages", () => {
    render(<ChatLayout {...defaultProps} />);

    expect(screen.getByText(/начните диалог/i)).toBeInTheDocument();
  });

  it("renders messages when provided", () => {
    const messages: MessageListItem[] = [
      {
        id: 1,
        session_id: "s1",
        role: "user",
        content: "Привет",
        sequence_order: 1,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(<ChatLayout {...defaultProps} messages={messages} />);

    expect(screen.getByText("Привет")).toBeInTheDocument();
  });

  it("disables message input when no sessionId (loading current dialog)", () => {
    render(<ChatLayout {...defaultProps} sessionId={null} />);

    expect(screen.getByPlaceholderText("Загрузка...")).toBeDisabled();
  });

  it("disables message input when sendLoading", () => {
    render(<ChatLayout {...defaultProps} sendLoading />);

    expect(screen.getByPlaceholderText("Напишите сообщение...")).toBeDisabled();
  });

  it("shows typing indicator when sendLoading is true", () => {
    render(<ChatLayout {...defaultProps} sendLoading />);

    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
