import { apiClient } from "./client";

export interface Question {
  id: number;
  stem: string;
  category: string;
  difficulty: number;
  reference_answer?: string;
  mastery_score: number;
  created_at: string;
}

export interface CreateQuestionPayload {
  stem: string;
  category: string;
  difficulty: number;
  /** 非空时后端不调用 AI 生成参考答案 */
  reference_answer?: string;
}

export interface QuestionFilters {
  category?: string;
  difficulty?: number;
  sort_by?: "created_at" | "mastery_score" | "recent_encountered" | "id";
  sort_order?: "asc" | "desc";
}

export interface QuestionPageResponse {
  total: number;
  page: number;
  page_size: number;
  items: Question[];
}

export interface UpdateQuestionPayload {
  stem: string;
  category: string;
  difficulty: number;
}

export interface PracticeRecord {
  id: number;
  session_id: number | null;
  question_id: number;
  user_answer: string;
  ai_answer: string;
  ai_score: number;
  created_at: string;
}

export async function fetchQuestions(filters?: QuestionFilters): Promise<Question[]> {
  const { data } = await apiClient.get<Question[]>("/api/questions", { params: filters });
  return data;
}

export async function fetchQuestionsPage(
  params: QuestionFilters & { page: number; page_size: number }
): Promise<QuestionPageResponse> {
  const { data } = await apiClient.get<QuestionPageResponse>("/api/questions/page", { params });
  return data;
}

export async function createQuestion(payload: CreateQuestionPayload): Promise<Question> {
  const { data } = await apiClient.post<Question>("/api/questions", payload);
  return data;
}

export async function updateQuestion(id: number, payload: UpdateQuestionPayload): Promise<Question> {
  const { data } = await apiClient.put<Question>(`/api/questions/${id}`, payload);
  return data;
}

export async function deleteQuestion(id: number): Promise<void> {
  await apiClient.delete(`/api/questions/${id}`);
}

export async function fetchQuestionRecords(questionId: number): Promise<PracticeRecord[]> {
  const { data } = await apiClient.get<PracticeRecord[]>(`/api/questions/${questionId}/records`);
  return data;
}

export async function refreshQuestionReferenceAnswer(questionId: number): Promise<Question> {
  const { data } = await apiClient.post<Question>(`/api/questions/${questionId}/refresh-reference`, null, {
    timeout: 120000
  });
  return data;
}

export interface BackfillReferenceAnswersResponse {
  scanned: number;
  updated: number;
  failed: Array<{ question_id: number; error: string }>;
}

export async function backfillReferenceAnswers(limit = 50): Promise<BackfillReferenceAnswersResponse> {
  const { data } = await apiClient.post<BackfillReferenceAnswersResponse>(
    `/api/questions/backfill-reference-answers`,
    null,
    { params: { limit }, timeout: 120000 }
  );
  return data;
}

