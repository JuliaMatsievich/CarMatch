import { apiClient } from './client';

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

export interface SendMessageResponse {
  id: number;
  session_id: string;
  role: string;
  content: string;
  sequence_order: number;
  created_at: string;
  extracted_params?: ExtractedParam[];
  ready_for_search?: boolean;
}

export async function createSession(): Promise<ChatSession> {
  const { data } = await apiClient.post<ChatSession>('/chat/sessions');
  return data;
}

export async function getSessions(): Promise<{ sessions: ChatSessionListItem[] }> {
  const { data } = await apiClient.get<{ sessions: ChatSessionListItem[] }>('/chat/sessions');
  return data;
}

export async function getMessages(sessionId: string): Promise<{ messages: MessageListItem[] }> {
  const { data } = await apiClient.get<{ messages: MessageListItem[] }>(
    `/chat/sessions/${sessionId}/messages`
  );
  return data;
}

export async function sendMessage(
  sessionId: string,
  content: string
): Promise<SendMessageResponse> {
  const { data } = await apiClient.post<SendMessageResponse>(
    `/chat/sessions/${sessionId}/messages`,
    { content }
  );
  return data;
}
