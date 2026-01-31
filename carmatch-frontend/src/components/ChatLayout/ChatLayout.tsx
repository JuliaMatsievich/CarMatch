import { ChatSidebar } from './ChatSidebar';
import { MessageList } from '../Chat/MessageList';
import { MessageInput } from '../Chat/MessageInput';
import type { ChatSessionListItem, MessageListItem } from '../../api/chat';
import type { CarResult } from '../../api/cars';
import { CarResults } from '../CarResults/CarResults';
import styles from './ChatLayout.module.css';

interface ChatLayoutProps {
  sessionId: string | null;
  sessions: ChatSessionListItem[];
  messages: MessageListItem[];
  cars: CarResult[];
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
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
  onSend,
  onLogout,
  sendLoading,
}: ChatLayoutProps) {
  return (
    <div className={styles.layout}>
      <ChatSidebar
        sessions={sessions}
        currentSessionId={sessionId}
        onNewChat={onNewChat}
        onSelectSession={onSelectSession}
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
        <MessageInput onSend={onSend} disabled={sendLoading || !sessionId} />
      </main>
    </div>
  );
}
