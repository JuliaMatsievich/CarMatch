import { apiClient } from './client';

export interface CarSearchParams {
  budget_max?: number;
  body_type?: string;
  min_year?: number;
  fuel_type?: string;
  transmission?: string;
  limit?: number;
}

export interface CarResult {
  id: number;
  mark_name: string;
  model_name: string;
  year: number | null;
  price_rub: number | null;
  body_type: string | null;
  fuel_type: string | null;
  transmission: string | null;
  images: string[];
  engine_volume?: number;
  horsepower?: number;
}

export interface CarSearchResponse {
  count: number;
  results: CarResult[];
}

export async function searchCars(params: CarSearchParams): Promise<CarSearchResponse> {
  const { data } = await apiClient.get<CarSearchResponse>('/cars/search', { params });
  return data;
}
