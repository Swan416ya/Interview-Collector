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
  /** AI 分类不在库中，已改为「未分类」或首个可用分类 */
  category_fallbacks?: number;
  /** 有岗位名不在库中，已剔除后入库 */
  role_lists_adjusted?: number;
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

