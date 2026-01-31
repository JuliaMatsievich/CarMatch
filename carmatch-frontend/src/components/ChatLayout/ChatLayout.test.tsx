import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatLayout } from "./ChatLayout";
import type { ChatSessionListItem, MessageListItem } from "../../api/chat";
import type { CarResult } from "../../api/cars";

describe("ChatLayout", () => {
  const defaultProps = {
    sessionId: "s1" as string | null,
    sessions: [] as ChatSessionListItem[],
    messages: [] as MessageListItem[],
    cars: [] as CarResult[],
    onNewChat: vi.fn(),
    onSelectSession: vi.fn(),
    onSend: vi.fn(),
    onLogout: vi.fn(),
    sendLoading: false,
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

  it("renders car results when cars provided", () => {
    const cars: CarResult[] = [
      {
        id: 1,
        mark_name: "Toyota",
        model_name: "Camry",
        year: 2020,
        price_rub: 2_500_000,
        body_type: null,
        fuel_type: null,
        images: null,
      },
    ];

    render(<ChatLayout {...defaultProps} cars={cars} />);

    expect(screen.getByText("Подобранные автомобили")).toBeInTheDocument();
    expect(screen.getByText("Toyota Camry")).toBeInTheDocument();
  });

  it("disables message input when no sessionId", () => {
    render(<ChatLayout {...defaultProps} sessionId={null} />);

    expect(screen.getByPlaceholderText("Напишите сообщение...")).toBeDisabled();
    expect(screen.getByRole("button", { name: /отправить/i })).toBeDisabled();
  });

  it("disables message input when sendLoading", () => {
    render(<ChatLayout {...defaultProps} sendLoading />);

    expect(screen.getByPlaceholderText("Напишите сообщение...")).toBeDisabled();
  });
});
