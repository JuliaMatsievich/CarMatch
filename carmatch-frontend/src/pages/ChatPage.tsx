import { useState, useCallback, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChatLayout } from "../components/ChatLayout/ChatLayout";
import { useAuth } from "../contexts/AuthContext";
import {
  createSession,
  getCurrentSession,
  getSessions,
  getMessages,
  sendMessage,
  deleteSession,
} from "../api/chat";
import { searchCars as searchCarsApi } from "../api/cars";
import type {
  MessageListItem,
  ChatSessionListItem,
  SendMessageResponse,
  ExtractedParam,
} from "../api/chat";
import type { CarResult } from "../api/cars";
import type { CarSearchParams } from "../api/cars";

const MIN_PARAMS_FOR_SEARCH = 3;

function extractedParamsToSearchParams(
  params: ExtractedParam[]
): CarSearchParams {
  const out: CarSearchParams = { limit: 10 };
  for (const p of params) {
    switch (p.type) {
      case "brand":
        if (p.value) out.brand = p.value;
        break;
      case "model":
        if (p.value) out.model = p.value;
        break;
      case "body_type":
        if (p.value) out.body_type = p.value;
        break;
      case "year":
        if (p.value) {
          const y = parseInt(p.value, 10);
          if (!Number.isNaN(y)) out.year = y;
        }
        break;
      case "modification":
        if (p.value) out.modification = p.value;
        break;
      case "transmission":
        if (p.value) out.transmission = p.value;
        break;
      case "fuel_type":
        if (p.value) out.fuel_type = p.value;
        break;
      case "engine_volume":
        if (p.value) {
          const v = parseFloat(p.value.replace(",", "."));
          if (!Number.isNaN(v)) out.engine_volume = v;
        }
        break;
      case "horsepower":
        if (p.value) {
          const h = parseInt(p.value, 10);
          if (!Number.isNaN(h)) out.horsepower = h;
        }
        break;
      default:
        break;
    }
  }
  return out;
}

export function ChatPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const { logout } = useAuth();
  const [sessions, setSessions] = useState<ChatSessionListItem[]>([]);
  const [messages, setMessages] = useState<MessageListItem[]>([]);
  const [cars, setCars] = useState<CarResult[]>([]);
  const [sendLoading, setSendLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);

  // На /chat без sessionId — получаем «текущий новый диалог» (пустая сессия или создаём одну) и переходим в неё
  useEffect(() => {
    if (sessionId) return;
    let cancelled = false;
    getCurrentSession()
      .then((session) => {
        if (!cancelled) {
          navigate(`/chat/${session.id}`, { replace: true });
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId, navigate]);

  // Загрузка списка сессий (для сайдбара)
  useEffect(() => {
    getSessions()
      .then((res) => setSessions(res.sessions))
      .catch(() => {});
  }, [sessionId]);

  // Загрузка сообщений при выборе сессии
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      setCars([]);
      return;
    }
    setLoadingMessages(true);
    getMessages(sessionId)
      .then((res) => {
        setMessages(res.messages);
        setCars([]);
      })
      .catch(() => setMessages([]))
      .finally(() => setLoadingMessages(false));
  }, [sessionId]);

  const handleNewChat = useCallback(() => {
    createSession().then((session) => {
      navigate(`/chat/${session.id}`, { replace: true });
      setMessages([]);
      setCars([]);
    });
  }, [navigate]);

  const handleSelectSession = useCallback(
    (id: string) => {
      navigate(`/chat/${id}`);
    },
    [navigate]
  );

  const handleDeleteSession = useCallback(
    async (id: string) => {
      try {
        await deleteSession(id);
        if (sessionId === id) {
          getCurrentSession().then((session) => {
            navigate(`/chat/${session.id}`, { replace: true });
          });
        }
      } finally {
        const res = await getSessions();
        setSessions(res.sessions);
      }
    },
    [sessionId, navigate]
  );

  const handleSend = useCallback(
    async (content: string) => {
      if (!sessionId) return;
      setSendLoading(true);
      const userMsg: MessageListItem = {
        id: 0,
        session_id: sessionId,
        role: "user",
        content,
        sequence_order: messages.length + 1,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      try {
        const res: SendMessageResponse = await sendMessage(sessionId, content);
        const hasCars = res.search_results && res.search_results.length > 0;
        // Когда уже подобранные автомобили — не показываем сообщение LLM, только карточки
        if (!hasCars) {
          const assistantMsg: MessageListItem = {
            id: res.id,
            session_id: res.session_id,
            role: res.role,
            content: res.content,
            sequence_order: res.sequence_order,
            created_at: res.created_at,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
        getSessions().then((res) => setSessions(res.sessions));
        if (hasCars) {
          setCars(res.search_results);
        } else if (
          res.ready_for_search &&
          res.extracted_params &&
          res.extracted_params.length >= MIN_PARAMS_FOR_SEARCH
        ) {
          const searchParams = extractedParamsToSearchParams(
            res.extracted_params
          );
          const carRes = await searchCarsApi(searchParams);
          setCars(carRes.results);
        } else {
          setCars([]);
        }
      } catch (err: unknown) {
        let errorText: string | null = null;
        if (err && typeof err === "object" && "response" in err) {
          const detail = (
            err as { response?: { data?: { detail?: string | string[] } } }
          ).response?.data?.detail;
          if (typeof detail === "string") errorText = detail;
          else if (Array.isArray(detail)) errorText = detail.join(". ");
        }
        const isTimeout =
          err &&
          typeof err === "object" &&
          "code" in err &&
          (err as { code?: string }).code === "ECONNABORTED";
        const fallback = isTimeout
          ? "Ответ занял слишком много времени. Попробуйте короче сообщение или позже."
          : "Не удалось получить ответ. Проверьте подключение и авторизацию или попробуйте позже.";
        setMessages((prev) => [
          ...prev,
          {
            id: 0,
            session_id: sessionId,
            role: "assistant",
            content: errorText ?? fallback,
            sequence_order: prev.length + 2,
            created_at: new Date().toISOString(),
          },
        ]);
        setCars([]);
      } finally {
        setSendLoading(false);
      }
    },
    [sessionId, messages.length]
  );

  const handleLogout = useCallback(() => {
    logout();
    navigate("/login", { replace: true });
  }, [logout, navigate]);

  return (
    <ChatLayout
      sessionId={sessionId ?? null}
      sessions={sessions}
      messages={messages}
      cars={cars}
      onNewChat={handleNewChat}
      onSelectSession={handleSelectSession}
      onDeleteSession={handleDeleteSession}
      onSend={handleSend}
      onLogout={handleLogout}
      sendLoading={sendLoading}
    />
  );
}
