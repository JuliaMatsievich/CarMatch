import { useEffect, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChatLayout } from "../components/ChatLayout/ChatLayout";
import { useAuth } from "../contexts/AuthContext";
import {
  createSession,
  getSessions,
  getMessages,
  sendMessage as sendMessageApi,
} from "../api/chat";
import { searchCars as searchCarsApi } from "../api/cars";
import type { ChatSessionListItem, MessageListItem } from "../api/chat";
import type { CarResult } from "../api/cars";

export default function ChatPage() {
  const { sessionId: paramSessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { token, logout } = useAuth();
  const [sessions, setSessions] = useState<ChatSessionListItem[]>([]);
  const [messages, setMessages] = useState<MessageListItem[]>([]);
  const [cars, setCars] = useState<CarResult[]>([]);
  const [sendLoading, setSendLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    try {
      const data = await getSessions();
      setSessions(data.sessions);
    } catch {
      setSessions([]);
    }
  }, []);

  const loadMessages = useCallback(async (id: string) => {
    try {
      const data = await getMessages(id);
      setMessages(data.messages);
    } catch {
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    loadSessions();
  }, [token, loadSessions]);

  useEffect(() => {
    if (!paramSessionId) return;
    loadMessages(paramSessionId);
    setCars([]);
  }, [paramSessionId, loadMessages]);

  useEffect(() => {
    if (!paramSessionId) {
      const createAndRedirect = async () => {
        try {
          const session = await createSession();
          navigate(`/chat/${session.id}`, { replace: true });
        } catch {
          setMessages([]);
        }
      };
      if (token) createAndRedirect();
    }
  }, [paramSessionId, token, navigate]);

  const handleNewChat = useCallback(async () => {
    try {
      const session = await createSession();
      navigate(`/chat/${session.id}`);
      setMessages([]);
      setCars([]);
      loadSessions();
    } catch {
      // ignore
    }
  }, [navigate, loadSessions]);

  const handleSelectSession = useCallback(
    (id: string) => {
      navigate(`/chat/${id}`);
    },
    [navigate]
  );

  const handleSend = useCallback(
    async (content: string) => {
      if (!paramSessionId) return;
      setSendLoading(true);
      const userMsg: MessageListItem = {
        id: -1,
        session_id: paramSessionId,
        role: "user",
        content,
        sequence_order: messages.length + 1,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      try {
        const res = await sendMessageApi(paramSessionId, content);
        const assistantMsg: MessageListItem = {
          id: res.id,
          session_id: res.session_id,
          role: res.role,
          content: res.content,
          sequence_order: res.sequence_order,
          created_at: res.created_at,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        if (
          res.ready_for_search &&
          res.extracted_params &&
          res.extracted_params.length >= 3
        ) {
          const params: Record<string, number | string | undefined> = {};
          res.extracted_params.forEach((p) => {
            if (p.type === "budget_max")
              params.budget_max = Number(p.value) || undefined;
            if (p.type === "body_type") params.body_type = p.value;
            if (p.type === "min_year")
              params.min_year = Number(p.value) || undefined;
            if (p.type === "fuel_type") params.fuel_type = p.value;
          });
          const searchRes = await searchCarsApi(params);
          setCars(searchRes.results);
        }
        loadSessions();
      } catch {
        setMessages((prev) => prev.filter((m) => m.id !== -1));
      } finally {
        setSendLoading(false);
      }
    },
    [paramSessionId, messages.length, loadSessions]
  );

  const handleLogout = useCallback(() => {
    logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  return (
    <ChatLayout
      sessionId={paramSessionId ?? null}
      sessions={sessions}
      messages={messages}
      cars={cars}
      onNewChat={handleNewChat}
      onSelectSession={handleSelectSession}
      onSend={handleSend}
      onLogout={handleLogout}
      sendLoading={sendLoading}
    />
  );
}
