import { useState, useCallback, useEffect } from "react";
import { ChatSidebar } from "./ChatSidebar";
import { MessageList } from "../Chat/MessageList";
import { MessageInput } from "../Chat/MessageInput";
import type { ChatSessionListItem, MessageListItem } from "../../api/chat";
import type { CarResult } from "../../api/cars";
import { CarResults } from "../CarResults/CarResults";
import styles from "./ChatLayout.module.css";

const SIDEBAR_COLLAPSED_KEY = "carmatch_sidebar_collapsed";

interface ChatLayoutProps {
  sessionId: string | null;
  sessions: ChatSessionListItem[];
  messages: MessageListItem[];
  cars: CarResult[];
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  onSend: (content: string) => void;
  onLogout: () => void;
  sendLoading?: boolean;
}

export function ChatLayout({
  sessionId,
  sessions,
  messages,
  cars,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onSend,
  onLogout,
  sendLoading,
}: ChatLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [sidebarCollapsed]);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((c) => !c);
  }, []);

  return (
    <div className={styles.layout}>
      <ChatSidebar
        sessions={sessions}
        currentSessionId={sessionId}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={toggleSidebar}
        onNewChat={onNewChat}
        onSelectSession={onSelectSession}
        onDeleteSession={onDeleteSession}
        onLogout={onLogout}
      />
      <main className={styles.main}>
        <div className={styles.messagesArea}>
          <MessageList messages={messages} />
          {cars.length > 0 && (
            <div className={styles.carResultsWrap}>
              <CarResults cars={cars} />
            </div>
          )}
        </div>
        {sendLoading && (
          <div
            className={styles.typingIndicator}
            role="status"
            aria-live="polite"
          >
            CatMatch подбирает машину....
          </div>
        )}
        <MessageInput
          onSend={onSend}
          disabled={sendLoading || !sessionId}
          disabledReason={!sessionId ? "Загрузка..." : undefined}
        />
      </main>
    </div>
  );
}
