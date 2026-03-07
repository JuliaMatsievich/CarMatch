import { apiClient } from "../../api/client";

export interface AdminCarItem {
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
  country?: string | null;
  images: string[];
  description?: string | null;
  brand_id?: number | null;
  model_id?: number | null;
  generation_id?: number | null;
  modification_id?: number | null;
  is_active: boolean;
}

export interface AdminCarListResponse {
  items: AdminCarItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminCarCreate {
  mark_name: string;
  model_name: string;
  body_type?: string | null;
  year?: number | null;
  price_rub?: number | null;
  fuel_type?: string | null;
  engine_volume?: number | null;
  horsepower?: number | null;
  modification?: string | null;
  transmission?: string | null;
  country?: string | null;
  description?: string | null;
  images?: string[] | null;
  is_active?: boolean;
}

export type AdminCarUpdate = Partial<AdminCarCreate>;

export interface AdminCarListParams {
  page?: number;
  per_page?: number;
  mark_name?: string;
  model_name?: string;
  body_type?: string;
  year_from?: number;
  year_to?: number;
  fuel_type?: string;
  transmission?: string;
   country?: string;
  is_active?: boolean;
  sort_by?: "mark_name" | "model_name" | "year";
  sort_dir?: "asc" | "desc";
}

export async function adminListCars(
  params: AdminCarListParams = {}
): Promise<AdminCarListResponse> {
  const { data } = await apiClient.get<AdminCarListResponse>("/admin/cars", {
    params,
  });
  return data;
}

export async function adminGetCar(carId: number): Promise<AdminCarItem> {
  const { data } = await apiClient.get<AdminCarItem>(`/admin/cars/${carId}`);
  return data;
}

export async function adminCreateCar(
  body: AdminCarCreate
): Promise<AdminCarItem> {
  const { data } = await apiClient.post<AdminCarItem>("/admin/cars", body);
  return data;
}

export async function adminUpdateCar(
  carId: number,
  body: AdminCarUpdate
): Promise<AdminCarItem> {
  const { data } = await apiClient.put<AdminCarItem>(
    `/admin/cars/${carId}`,
    body
  );
  return data;
}

export async function adminDeleteCar(carId: number): Promise<void> {
  await apiClient.delete(`/admin/cars/${carId}`);
}

