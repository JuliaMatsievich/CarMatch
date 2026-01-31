import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageList } from "./MessageList";
import type { MessageListItem } from "../../api/chat";

describe("MessageList", () => {
  it("shows empty state when no messages", () => {
    render(<MessageList messages={[]} />);

    expect(screen.getByText(/начните диалог/i)).toBeInTheDocument();
  });

  it("renders messages in sequence order", () => {
    const messages: MessageListItem[] = [
      {
        id: 1,
        session_id: "s1",
        role: "user",
        content: "Ищу седан до 1 млн",
        sequence_order: 1,
        created_at: "2024-01-01T00:00:00Z",
      },
      {
        id: 2,
        session_id: "s1",
        role: "assistant",
        content: "Понял, подбираю варианты",
        sequence_order: 2,
        created_at: "2024-01-01T00:00:01Z",
      },
    ];

    render(<MessageList messages={messages} />);

    expect(screen.getByText("Ищу седан до 1 млн")).toBeInTheDocument();
    expect(screen.getByText("Понял, подбираю варианты")).toBeInTheDocument();
  });

  it("sorts messages by sequence_order", () => {
    const messages: MessageListItem[] = [
      {
        id: 2,
        session_id: "s1",
        role: "assistant",
        content: "Второе сообщение",
        sequence_order: 2,
        created_at: "2024-01-01T00:00:01Z",
      },
      {
        id: 1,
        session_id: "s1",
        role: "user",
        content: "Первое сообщение",
        sequence_order: 1,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(<MessageList messages={messages} />);

    const listItems = screen.getAllByRole("listitem");
    expect(listItems[0]).toHaveTextContent("Первое сообщение");
    expect(listItems[1]).toHaveTextContent("Второе сообщение");
  });

  it("shows role labels correctly", () => {
    const messages: MessageListItem[] = [
      {
        id: 1,
        session_id: "s1",
        role: "user",
        content: "Тест",
        sequence_order: 1,
        created_at: "2024-01-01T00:00:00Z",
      },
    ];

    render(<MessageList messages={messages} />);

    expect(screen.getByText("Вы")).toBeInTheDocument();
    expect(screen.getByText("Тест")).toBeInTheDocument();
  });
});
