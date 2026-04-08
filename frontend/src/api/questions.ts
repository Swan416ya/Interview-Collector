import { apiClient } from "./client";

export interface Question {
  id: number;
  stem: string;
  category: string;
  difficulty: number;
}

export interface CreateQuestionPayload {
  stem: string;
  category: string;
  difficulty: number;
}

export async function fetchQuestions(): Promise<Question[]> {
  const { data } = await apiClient.get<Question[]>("/api/questions");
  return data;
}

export async function createQuestion(payload: CreateQuestionPayload): Promise<Question> {
  const { data } = await apiClient.post<Question>("/api/questions", payload);
  return data;
}

