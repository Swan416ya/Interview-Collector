import { apiClient } from "./client";

export interface KbCitation {
  chunk_id: number;
  question_id: number;
  excerpt: string;
  source_type: string;
}

export interface KbQueryResponse {
  answer: string;
  citations: KbCitation[];
}

export async function postKbQuery(query: string, topK = 5): Promise<KbQueryResponse> {
  const res = await apiClient.post<KbQueryResponse>(
    "/api/kb/query",
    { query: query.trim(), top_k: topK },
    { timeout: 120000 }
  );
  return res.data;
}

export async function postKbReindex(): Promise<{ questions_processed: number }> {
  const res = await apiClient.post<{ questions_processed: number }>("/api/kb/reindex");
  return res.data;
}
