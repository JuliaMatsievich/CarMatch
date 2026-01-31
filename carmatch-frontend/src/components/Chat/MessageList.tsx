import type { MessageListItem } from '../../api/chat';
import styles from './MessageList.module.css';

interface MessageListProps {
  messages: MessageListItem[];
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className={styles.empty}>
        <p>Начните диалог — опишите, какой автомобиль ищете (бюджет, тип кузова, топливо и т.д.).</p>
      </div>
    );
  }

  return (
    <ul className={styles.list}>
      {messages
        .slice()
        .sort((a, b) => a.sequence_order - b.sequence_order)
        .map((m) => (
          <li key={m.id} className={m.role === 'user' ? styles.userMessage : styles.assistantMessage}>
            <span className={styles.role}>{m.role === 'user' ? 'Вы' : 'CarMatch'}</span>
            <p className={styles.content}>{m.content}</p>
          </li>
        ))}
    </ul>
  );
}
