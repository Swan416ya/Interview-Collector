import { apiClient } from "./client";

export interface NamedEntity {
  id: number;
  name: string;
}

export async function fetchCategories(): Promise<NamedEntity[]> {
  const { data } = await apiClient.get<NamedEntity[]>("/api/categories");
  return data;
}

export async function createCategory(name: string): Promise<NamedEntity> {
  const { data } = await apiClient.post<NamedEntity>("/api/categories", { name });
  return data;
}

export async function fetchRoles(): Promise<NamedEntity[]> {
  const { data } = await apiClient.get<NamedEntity[]>("/api/roles");
  return data;
}

export async function createRole(name: string): Promise<NamedEntity> {
  const { data } = await apiClient.post<NamedEntity>("/api/roles", { name });
  return data;
}

