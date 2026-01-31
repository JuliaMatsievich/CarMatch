import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ChatLayout } from "../components/ChatLayout/ChatLayout";
import { useAuth } from "../contexts/AuthContext";
import { chatComplete } from "../api/chat";
import type { MessageListItem } from "../api/chat";

/** Локальное сообщение для отображения в списке (совместимо с MessageListItem). */
function toMessageItem(
  role: "user" | "assistant",
  content: string,
  index: number
): MessageListItem {
  return {
    id: index,
    session_id: "",
    role,
    content,
    sequence_order: index + 1,
    created_at: new Date().toISOString(),
  };
}

export default function ChatPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [messages, setMessages] = useState<MessageListItem[]>([]);
  const [sendLoading, setSendLoading] = useState(false);

  const handleNewChat = useCallback(() => {
    setMessages([]);
  }, []);

  const handleSend = useCallback(
    async (content: string) => {
      setSendLoading(true);
      const userMsg = toMessageItem("user", content, messages.length);
      setMessages((prev) => [...prev, userMsg]);
      const history = [...messages, userMsg].map((m) => ({
        role: m.role as "user" | "assistant",
        content: m.content,
      }));
      try {
        const res = await chatComplete(history);
        const assistantMsg = toMessageItem(
          "assistant",
          res.content,
          messages.length + 1
        );
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err: unknown) {
        // Сообщение пользователя не удаляем — показываем ошибку ответом ассистента
        let errorText: string | null = null;
        if (err && typeof err === "object" && "response" in err) {
          const detail = (
            err as { response?: { data?: { detail?: string | string[] } } }
          ).response?.data?.detail;
          if (typeof detail === "string") errorText = detail;
          else if (Array.isArray(detail)) errorText = detail.join(". ");
        }
        const fallback =
          "Не удалось получить ответ. Проверьте подключение к серверу и авторизацию или попробуйте позже.";
        const assistantError = toMessageItem(
          "assistant",
          errorText ?? fallback,
          messages.length + 1
        );
        setMessages((prev) => [...prev, assistantError]);
      } finally {
        setSendLoading(false);
      }
    },
    [messages]
  );

  const handleLogout = useCallback(() => {
    logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  return (
    <ChatLayout
      sessionId="current"
      sessions={[]}
      messages={messages}
      cars={[]}
      onNewChat={handleNewChat}
      onSelectSession={() => {}}
      onSend={handleSend}
      onLogout={handleLogout}
      sendLoading={sendLoading}
    />
  );
}
