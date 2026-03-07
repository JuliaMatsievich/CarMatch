import { apiClient } from "../../api/client";
import type { SendMessageCarResult } from "../../api/chat";

export interface AdminSessionListItem {
  id: string;
  user_id: number;
  user_email: string;
  created_at: string;
  message_count: number;
  display_status: string;
  extracted_params_summary: string;
  cars_found: number;
}

export interface AdminSessionListResponse {
  items: AdminSessionListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminSessionListParams {
  page?: number;
  per_page?: number;
  user_id?: number;
  status?: string;
  date_from?: string;
  date_to?: string;
}

export interface AdminSessionMessage {
  id: number;
  role: string;
  content: string;
  sequence_order: number;
  created_at: string;
  ai_metadata?: Record<string, unknown> | null;
}

export interface AdminSessionDetail {
  id: string;
  user_id: number;
  user_email: string;
  status: string;
  display_status: string;
  extracted_params: Record<string, unknown>;
  search_results: SendMessageCarResult[];
  created_at: string;
  message_count: number;
  cars_found: number;
}

export interface AdminSessionDetailResponse {
  session: AdminSessionDetail;
  messages: AdminSessionMessage[];
}

export async function adminListSessions(
  params: AdminSessionListParams = {}
): Promise<AdminSessionListResponse> {
  const { data } = await apiClient.get<AdminSessionListResponse>(
    "/admin/sessions",
    { params }
  );
  return data;
}

export async function adminGetSessionDetail(
  sessionId: string
): Promise<AdminSessionDetailResponse> {
  const { data } = await apiClient.get<AdminSessionDetailResponse>(
    `/admin/sessions/${sessionId}`
  );
  return data;
}

export async function adminGetSessionMessages(
  sessionId: string
): Promise<AdminSessionMessage[]> {
  const { data } = await apiClient.get<AdminSessionMessage[]>(
    `/admin/sessions/${sessionId}/messages`
  );
  return data;
}

export async function adminDeleteSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/admin/sessions/${sessionId}`);
}

