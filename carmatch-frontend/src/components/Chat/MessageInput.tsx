import { useState } from "react";
import styles from "./MessageInput.module.css";

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  disabledReason?: string;
}

export function MessageInput({
  onSend,
  disabled,
  disabledReason,
}: MessageInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const placeholder =
    disabled && disabledReason ? disabledReason : "Напишите сообщение...";

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input
        type="text"
        className={styles.input}
        placeholder={placeholder}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        autoComplete="off"
        aria-label="Сообщение в чат"
      />
      <button
        type="submit"
        className={styles.submitBtn}
        disabled={disabled || !value.trim()}
      >
        Отправить
      </button>
    </form>
  );
}
