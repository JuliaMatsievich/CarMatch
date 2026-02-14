import { apiClient } from "./client";

/** Сообщение для свободного чата с DeepSeek (без сессий в БД). */
export interface ChatCompleteMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatCompleteResponse {
  content: string;
}

export async function chatComplete(
  messages: ChatCompleteMessage[]
): Promise<ChatCompleteResponse> {
  const { data } = await apiClient.post<ChatCompleteResponse>("chat/complete", {
    messages,
  });
  return data;
}

export interface ChatSession {
  id: string;
  user_id: number;
  status: string;
  extracted_params: Record<string, unknown>;
  search_results: unknown[];
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListItem {
  id: string;
  status: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface MessageListItem {
  id: number;
  session_id: string;
  role: string;
  content: string;
  sequence_order: number;
  created_at: string;
}

export interface ExtractedParam {
  type: string;
  value: string;
  confidence: number;
}

/** Автомобиль из ответа поиска по БД (совпадает с CarResult из /cars/search). */
export interface SendMessageCarResult {
  id: number;
  mark_name: string;
  model_name: string;
  year: number | null;
  price_rub: number | null;
  body_type: string | null;
  fuel_type: string | null;
  engine_volume?: number | null;
  horsepower?: number | null;
  modification: string | null;
  transmission: string | null;
  images: string[];
  description?: string | null;
}

export interface SendMessageResponse {
  id: number;
  session_id: string;
  role: string;
  content: string;
  sequence_order: number;
  created_at: string;
  extracted_params?: ExtractedParam[];
  ready_for_search?: boolean;
  /** Автомобили из БД по результатам поиска (то же, что в тексте ответа). */
  search_results?: SendMessageCarResult[];
}

export async function createSession(): Promise<ChatSession> {
  const { data } = await apiClient.post<ChatSession>("/chat/sessions");
  return data;
}

export async function getCurrentSession(): Promise<ChatSession> {
  const { data } = await apiClient.get<ChatSession>("/chat/sessions/current");
  return data;
}

export async function getSessions(): Promise<{
  sessions: ChatSessionListItem[];
}> {
  const { data } = await apiClient.get<{ sessions: ChatSessionListItem[] }>(
    "/chat/sessions"
  );
  return data;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/chat/sessions/${sessionId}`);
}

export async function getMessages(
  sessionId: string
): Promise<{ messages: MessageListItem[] }> {
  const { data } = await apiClient.get<{ messages: MessageListItem[] }>(
    `/chat/sessions/${sessionId}/messages`
  );
  return data;
}

/** Таймаут отправки сообщения (мс): бэкенд делает 2 запроса к LLM, ответ может идти 1–2 мин. */
const SEND_MESSAGE_TIMEOUT_MS = 120_000;

export async function sendMessage(
  sessionId: string,
  content: string
): Promise<SendMessageResponse> {
  const { data } = await apiClient.post<SendMessageResponse>(
    `/chat/sessions/${sessionId}/messages`,
    { content },
    { timeout: SEND_MESSAGE_TIMEOUT_MS }
  );
  return data;
}
