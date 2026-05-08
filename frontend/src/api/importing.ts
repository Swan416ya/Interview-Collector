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
  chunk_count?: number;
  chunk_error_count?: number;
  chunk_errors?: unknown[];
  /** 本请求命中 import 抽取缓存的 chunk 数 */
  extract_cache_hits?: number;
  /** 本请求实际调用 AI 抽取的 chunk 数 */
  extract_cache_misses?: number;
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

export type ImportRowStatus = "idle" | "loading" | "ok" | "err";

export interface ImportCommitOneResponse {
  id: number;
  stem: string;
  category: string;
  difficulty: number;
  category_fallback: boolean;
  roles_adjusted: boolean;
  linked_roles: number;
  linked_companies: number;
  created_companies: number;
}

export async function fetchPromptTemplate(): Promise<PromptTemplateResponse> {
  const { data } = await apiClient.get<PromptTemplateResponse>("/api/import/prompt-template");
  return data;
}

export async function commitImport(payload: unknown): Promise<ImportCommitResponse> {
  const { data } = await apiClient.post<ImportCommitResponse>("/api/import/commit", payload);
  return data;
}

export async function commitImportOne(item: PreviewQuestionItem): Promise<ImportCommitOneResponse> {
  const { data } = await apiClient.post<ImportCommitOneResponse>(
    "/api/import/commit-one",
    {
      stem: item.stem,
      category_name: item.category_name,
      roles: item.roles ?? [],
      companies: item.companies ?? [],
      difficulty: item.difficulty
    },
    { timeout: 120000 }
  );
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

