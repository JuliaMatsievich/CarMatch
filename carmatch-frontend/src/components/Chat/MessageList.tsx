import { useEffect, useRef } from "react";
import { Car, User } from "lucide-react";
import type { MessageListItem } from "../../api/chat";
import styles from "./MessageList.module.css";

interface MessageListProps {
  messages: MessageListItem[];
}

export function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = endRef.current;
    if (el?.scrollIntoView) {
      el.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className={styles.empty}>
        <p>
          Начните диалог — опишите, какой автомобиль ищете (бюджет, тип кузова,
          топливо и т.д.).
        </p>
      </div>
    );
  }

  return (
    <>
      <ul className={styles.list}>
        {messages
          .slice()
          .sort((a, b) => a.sequence_order - b.sequence_order)
          .map((m) => (
            <li
              key={`msg-${m.id}-${m.sequence_order}`}
              className={m.role === "user" ? styles.userRow : styles.assistantRow}
            >
              {m.role === "user" ? null : (
                <span className={styles.iconWrap} aria-hidden>
                  <Car size={20} className={styles.iconCar} />
                </span>
              )}
              <div
                className={
                  m.role === "user" ? styles.userMessage : styles.assistantMessage
                }
              >
                <span className={styles.role}>
                  {m.role === "user" ? "Вы" : "CarMatch"}
                </span>
                <p className={styles.content}>{m.content}</p>
              </div>
              {m.role === "user" ? (
                <span className={styles.iconWrap} aria-hidden>
                  <User size={20} className={styles.iconUser} />
                </span>
              ) : null}
            </li>
          ))}
      </ul>
      <div ref={endRef} />
    </>
  );
}
