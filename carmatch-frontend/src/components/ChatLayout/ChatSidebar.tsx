import {
  Car,
  LogOut,
  Menu,
  MessageCircle,
  MessageSquarePlus,
  Trash2,
} from "lucide-react";
import type { ChatSessionListItem } from "../../api/chat";
import styles from "./ChatLayout.module.css";

const DEFAULT_TITLE = "Новый диалог";

interface ChatSidebarProps {
  sessions: ChatSessionListItem[];
  currentSessionId: string | null;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  onDeleteSession?: (id: string) => void;
  onLogout: () => void;
}

export function ChatSidebar({
  sessions,
  currentSessionId,
  collapsed = false,
  onToggleCollapsed,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onLogout,
}: ChatSidebarProps) {
  return (
    <aside
      className={collapsed ? styles.sidebarCollapsed : styles.sidebar}
      aria-label="Боковая панель диалогов"
    >
      <div className={styles.sidebarHeader}>
        {collapsed ? (
          <>
            <div className={styles.logoIconOnly} aria-hidden>
              <div className={styles.carIconBg}>
                <Car className={styles.carIcon} />
              </div>
            </div>
            <button
              type="button"
              className={styles.sidebarToggle}
              onClick={onToggleCollapsed}
              aria-label="Развернуть панель"
              title="Развернуть панель"
            >
              <Menu size={20} aria-hidden />
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className={styles.sidebarToggle}
              onClick={onToggleCollapsed}
              aria-label="Свернуть панель"
              title="Свернуть панель"
            >
              <Menu size={20} aria-hidden />
            </button>
            <div className={styles.logoWithIcon}>
              <div className={styles.carIconBg}>
                <Car className={styles.carIcon} />
              </div>
              <h1 className={styles.sidebarTitle}>CarMatch</h1>
            </div>
          </>
        )}
      </div>
      <button
        type="button"
        className={styles.newChatBtn}
        onClick={onNewChat}
        title="Новый диалог"
      >
        {collapsed ? (
          <MessageSquarePlus size={20} aria-hidden />
        ) : (
          "Новый диалог"
        )}
      </button>
      <ul className={styles.sessionList}>
        {sessions.map((s) => (
          <li key={s.id} className={styles.sessionListItem}>
            <button
              type="button"
              className={
                currentSessionId === s.id
                  ? styles.sessionItemActive
                  : styles.sessionItem
              }
              onClick={() => onSelectSession(s.id)}
              title={s.title || DEFAULT_TITLE}
            >
              {collapsed ? (
                <MessageCircle
                  size={18}
                  className={styles.sessionItemIcon}
                  aria-hidden
                />
              ) : (
                <>
                  <span className={styles.sessionTitle}>
                    {(s.title || DEFAULT_TITLE).trim() || DEFAULT_TITLE}
                  </span>
                  <span className={styles.sessionMeta}>
                    {s.message_count} сообщ.
                  </span>
                </>
              )}
            </button>
            {!collapsed && onDeleteSession && (
              <button
                type="button"
                className={styles.deleteSessionBtn}
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(s.id);
                }}
                aria-label="Удалить диалог"
                title="Удалить диалог"
              >
                <Trash2 size={16} aria-hidden />
              </button>
            )}
          </li>
        ))}
      </ul>
      <div className={styles.sidebarFooter}>
        <button
          type="button"
          className={styles.logoutBtn}
          onClick={onLogout}
          title="Выйти"
        >
          {collapsed ? <LogOut size={18} aria-hidden /> : "Выйти"}
        </button>
      </div>
    </aside>
  );
}
