import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatSidebar } from "./ChatSidebar";
import type { ChatSessionListItem } from "../../api/chat";

describe("ChatSidebar", () => {
  const defaultProps = {
    sessions: [] as ChatSessionListItem[],
    currentSessionId: null as string | null,
    onNewChat: vi.fn(),
    onSelectSession: vi.fn(),
    onLogout: vi.fn(),
  };

  it("renders logo and title", () => {
    render(<ChatSidebar {...defaultProps} />);

    expect(screen.getByText("CarMatch")).toBeInTheDocument();
  });

  it("renders new chat button", () => {
    render(<ChatSidebar {...defaultProps} />);

    expect(
      screen.getByRole("button", { name: /новый диалог/i })
    ).toBeInTheDocument();
  });

  it("calls onNewChat when new chat button clicked", async () => {
    const user = userEvent.setup();
    const onNewChat = vi.fn();
    render(<ChatSidebar {...defaultProps} onNewChat={onNewChat} />);

    await user.click(screen.getByRole("button", { name: /новый диалог/i }));

    expect(onNewChat).toHaveBeenCalledTimes(1);
  });

  it("calls onLogout when logout button clicked", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    render(<ChatSidebar {...defaultProps} onLogout={onLogout} />);

    await user.click(screen.getByRole("button", { name: /выйти/i }));

    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it("renders session list with title", () => {
    const sessions: ChatSessionListItem[] = [
      {
        id: "s1",
        status: "active",
        title: "Подбор авто до 2 млн",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        message_count: 5,
      },
    ];

    render(<ChatSidebar {...defaultProps} sessions={sessions} />);

    expect(screen.getByText("Подбор авто до 2 млн")).toBeInTheDocument();
    expect(screen.getByText("5 сообщ.")).toBeInTheDocument();
  });

  it("shows default title when session has no title", () => {
    const sessions: ChatSessionListItem[] = [
      {
        id: "s1",
        status: "active",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        message_count: 1,
      },
    ];

    render(<ChatSidebar {...defaultProps} sessions={sessions} />);

    const sessionButton = screen.getByRole("button", {
      name: /новый диалог.*1 сообщ/i,
    });
    expect(sessionButton).toBeInTheDocument();
  });

  it("calls onSelectSession when session clicked", async () => {
    const user = userEvent.setup();
    const onSelectSession = vi.fn();
    const sessions: ChatSessionListItem[] = [
      {
        id: "s1",
        status: "active",
        title: "Чат",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        message_count: 3,
      },
    ];

    render(
      <ChatSidebar
        {...defaultProps}
        sessions={sessions}
        currentSessionId={null}
        onSelectSession={onSelectSession}
      />
    );

    const sessionButton = screen.getByRole("button", {
      name: /чат.*3 сообщ/i,
    });
    await user.click(sessionButton);

    expect(onSelectSession).toHaveBeenCalledWith("s1");
  });

  it("marks current session as active", () => {
    const sessions: ChatSessionListItem[] = [
      {
        id: "s1",
        status: "active",
        title: "Текущий",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        message_count: 2,
      },
    ];

    render(
      <ChatSidebar
        {...defaultProps}
        sessions={sessions}
        currentSessionId="s1"
      />
    );

    const sessionButton = screen.getByRole("button", {
      name: /текущий.*2 сообщ/i,
    });
    expect(sessionButton.className).toMatch(/sessionItemActive|active/i);
  });

  it("calls onDeleteSession when delete button clicked", async () => {
    const user = userEvent.setup();
    const onDeleteSession = vi.fn();
    const sessions: ChatSessionListItem[] = [
      {
        id: "s1",
        status: "active",
        title: "Удаляемый",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        message_count: 1,
      },
    ];

    render(
      <ChatSidebar
        {...defaultProps}
        sessions={sessions}
        onDeleteSession={onDeleteSession}
      />
    );

    const deleteBtn = screen.getByRole("button", { name: /удалить диалог/i });
    await user.click(deleteBtn);

    expect(onDeleteSession).toHaveBeenCalledTimes(1);
    expect(onDeleteSession).toHaveBeenCalledWith("s1");
  });

  it("does not show delete button when onDeleteSession is not passed", () => {
    const sessions: ChatSessionListItem[] = [
      {
        id: "s1",
        status: "active",
        title: "Без удаления",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        message_count: 1,
      },
    ];

    render(<ChatSidebar {...defaultProps} sessions={sessions} />);

    expect(
      screen.queryByRole("button", { name: /удалить диалог/i })
    ).not.toBeInTheDocument();
  });
});
