import { apiClient } from "../../api/client";
import type { AdminSessionListResponse } from "./adminSessions";

export interface AdminUserListItem {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
  login_count: number;
  sessions_count: number;
}

export interface AdminUserListResponse {
  items: AdminUserListItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminUserListParams {
  page?: number;
  per_page?: number;
  email?: string;
  is_active?: boolean;
}

export async function adminListUsers(
  params: AdminUserListParams = {}
): Promise<AdminUserListResponse> {
  const { data } = await apiClient.get<AdminUserListResponse>("/admin/users", {
    params,
  });
  return data;
}

export async function adminDeleteUser(userId: number): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}`);
}

export async function adminListUserSessions(
  userId: number,
  page?: number,
  perPage?: number
): Promise<AdminSessionListResponse> {
  const { data } = await apiClient.get<AdminSessionListResponse>(
    `/admin/users/${userId}/sessions`,
    { params: { page, per_page: perPage } }
  );
  return data;
}

