import { apiClient } from "./client";

export interface PromptTemplateResponse {
  prompt: string;
  allowed_categories: string[];
  allowed_roles: string[];
}

export interface PreviewQuestionItem {
  stem: string;
  category_name: string;
  roles: string[];
  companies: string[];
  difficulty: number;
}

export interface ImportPreviewResponse {
  questions: PreviewQuestionItem[];
  allowed_categories: string[];
  allowed_roles: string[];
}

export interface ImportCommitResponse {
  created_questions: number;
  created_companies: number;
  linked_roles: number;
  linked_companies: number;
}

export async function fetchPromptTemplate(): Promise<PromptTemplateResponse> {
  const { data } = await apiClient.get<PromptTemplateResponse>("/api/import/prompt-template");
  return data;
}

export async function commitImport(payload: unknown): Promise<ImportCommitResponse> {
  const { data } = await apiClient.post<ImportCommitResponse>("/api/import/commit", payload);
  return data;
}

export async function previewImport(rawText: string): Promise<ImportPreviewResponse> {
  const { data } = await apiClient.post<ImportPreviewResponse>("/api/import/preview", {
    raw_text: rawText
  }, {
    timeout: 120000
  });
  return data;
}

