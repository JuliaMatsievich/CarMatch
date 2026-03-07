import { useState, useCallback, useEffect, useRef } from "react";
import { ChatSidebar } from "./ChatSidebar";
import { MessageList } from "../Chat/MessageList";
import { MessageInput } from "../Chat/MessageInput";
import type { ChatSessionListItem, MessageListItem } from "../../api/chat";
import styles from "./ChatLayout.module.css";
import { SEARCH_HINT_MESSAGES } from "../../constants/searchMessages";

const SIDEBAR_COLLAPSED_KEY = "carmatch_sidebar_collapsed";

interface ChatLayoutProps {
  sessionId: string | null;
  sessions: ChatSessionListItem[];
  messages: MessageListItem[];
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  onSend: (content: string) => void;
  onLogout: () => void;
  sendLoading?: boolean;
  userEmail?: string | null;
}

export function ChatLayout({
  sessionId,
  sessions,
  messages,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onSend,
  onLogout,
  sendLoading,
  userEmail,
}: ChatLayoutProps) {
  const [hintMessage, setHintMessage] = useState<string | null>(null);
  const hintsRef = useRef<string[]>([]);
  const hintIndexRef = useRef(0);
  const intervalRef = useRef<number | null>(null);

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

  useEffect(() => {
    if (sendLoading) {
      // Подготовить случайный порядок сообщений при каждом запуске поиска
      const shuffled = SEARCH_HINT_MESSAGES.slice().sort(() => Math.random() - 0.5);
      hintsRef.current = shuffled;
      hintIndexRef.current = 0;
      setHintMessage(shuffled[0] ?? null);

      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
      }
      intervalRef.current = window.setInterval(() => {
        const hints = hintsRef.current;
        if (!hints.length) return;
        hintIndexRef.current = (hintIndexRef.current + 1) % hints.length;
        setHintMessage(hints[hintIndexRef.current] ?? null);
      }, 3000);
    } else {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setHintMessage(null);
    }

    return () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [sendLoading]);

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
        userEmail={userEmail ?? null}
      />
      <main className={styles.main}>
        <div className={styles.messagesArea}>
          <MessageList messages={messages} />
        </div>
        {sendLoading && hintMessage && (
          <div
            className={styles.typingIndicator}
            role="status"
            aria-live="polite"
          >
            {hintMessage}
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
