import { apiClient } from "./client";

export interface Question {
  id: number;
  stem: string;
  category: string;
  difficulty: number;
  mastery_score: number;
  created_at: string;
}

export interface CreateQuestionPayload {
  stem: string;
  category: string;
  difficulty: number;
}

export interface QuestionFilters {
  category?: string;
  difficulty?: number;
  sort_by?: "created_at" | "mastery_score";
  sort_order?: "asc" | "desc";
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

