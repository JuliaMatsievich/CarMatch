import { apiClient } from './client';

export interface CarSearchParams {
  brand?: string;
  model?: string;
  body_type?: string;
  year?: number;
  modification?: string;
  transmission?: string;
  fuel_type?: string;
  engine_volume?: number;
  horsepower?: number;
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
  engine_volume?: number | null;
  horsepower?: number | null;
  modification: string | null;   // полная строка модификации (например "1.6d MT 90 л.с.")
  transmission: string | null;    // тип коробки: MT, AMT, CVT и т.д.
  images: string[];
  description?: string | null;
  brand_id?: number;
  model_id?: number;
  generation_id?: number;
  modification_id?: number;
}

export interface CarSearchResponse {
  count: number;
  results: CarResult[];
}

export async function searchCars(params: CarSearchParams): Promise<CarSearchResponse> {
  const { data } = await apiClient.get<CarSearchResponse>('/cars/search', { params });
  return data;
}
