import { useEffect, useRef } from "react";
import { Car, FileText, Sparkles, User } from "lucide-react";
import type { MessageListItem } from "../../api/chat";
import type { SendMessageCarResult } from "../../api/chat";
import styles from "./MessageList.module.css";

/** Первая строка: марка, модель, кузов (модификация), год. */
function formatCarTitle(car: SendMessageCarResult): string {
  const parts: string[] = [car.mark_name, car.model_name].filter(Boolean);
  const mid: string[] = [];
  if (car.body_type) mid.push(car.body_type);
  if (car.modification) mid.push(`(${car.modification})`);
  if (mid.length) parts.push(mid.join(" "));
  if (car.year != null) parts.push(String(car.year));
  return parts.join(", ") + (parts.length ? "." : "");
}

/** Убираем из описания дубликат заголовка и фразу про страну. */
function descriptionWithoutTitleAndCountry(description: string, car: SendMessageCarResult): string {
  if (!description?.trim()) return "";
  let text = description.trim();
  const title = formatCarTitle(car);
  if (title && (text.startsWith(title) || text.startsWith(title.replace(/\s*\.\s*$/, "")))) {
    text = text.slice(title.length).replace(/^[\s.,]+/, "");
  }
  if (car.mark_name && text.startsWith(car.mark_name)) {
    const dot = text.indexOf(". ");
    if (dot !== -1) text = text.slice(dot + 2).trim();
  }
  text = text
    .replace(/\bВыпускается\s+в\s+[^.]+\.?\s*/gi, "")
    .replace(/Производство\s*[—\-]\s*[^.]+\.?\s*/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  return text;
}

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
              <div className={m.role === "user" ? styles.userBubble : styles.assistantBubble}>
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
