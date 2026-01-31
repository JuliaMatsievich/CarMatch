import { Car } from 'lucide-react';
import type { ChatSessionListItem } from '../../api/chat';
import styles from './ChatLayout.module.css';

interface ChatSidebarProps {
  sessions: ChatSessionListItem[];
  currentSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onLogout: () => void;
}

export function ChatSidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  onLogout,
}: ChatSidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <div className={styles.logoWithIcon}>
          <div className={styles.carIconBg}>
            <Car className={styles.carIcon} />
          </div>
          <h1 className={styles.sidebarTitle}>CarMatch</h1>
        </div>
      </div>
      <button type="button" className={styles.newChatBtn} onClick={onNewChat}>
        Новый диалог
      </button>
      <ul className={styles.sessionList}>
        {sessions.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className={currentSessionId === s.id ? styles.sessionItemActive : styles.sessionItem}
              onClick={() => onSelectSession(s.id)}
            >
              <span className={styles.sessionTitle}>Диалог</span>
              <span className={styles.sessionMeta}>{s.message_count} сообщ.</span>
            </button>
          </li>
        ))}
      </ul>
      <div className={styles.sidebarFooter}>
        <button type="button" className={styles.logoutBtn} onClick={onLogout}>
          Выйти
        </button>
      </div>
    </aside>
  );
}
