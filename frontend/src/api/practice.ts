import { apiClient } from "./client";
import type { Question } from "./questions";

export interface PracticeStartResponse {
  session_id: number;
  questions: Question[];
  question_count: number;
}

export interface PracticeCategoryOption {
  category: string;
  total_questions: number;
  selectable: boolean;
}

export interface PracticeCategoriesResponse {
  categories: PracticeCategoryOption[];
  total_questions_all: number;
}

export interface PracticeRecord {
  id: number;
  session_id: number | null;
  question_id: number;
  user_answer: string;
  ai_answer: string;
  ai_score: number; // 0-10
  created_at: string;
}

export interface PracticeSubmitResponse {
  record: PracticeRecord;
  analysis: string;
  reference_answer: string;
}

export interface PracticeSummaryResponse {
  session_id: number;
  total_score: number;
  record_ids: number[];
  completed_at: string | null;
  question_count?: number;
}

export interface PracticeSessionListItem {
  id: number;
  total_score: number;
  question_count?: number;
  completed_at: string | null;
  created_at: string;
}

export interface PracticeActivityDay {
  date: string;
  count: number;
  level: number;
}

export interface PracticeActivityResponse {
  timezone: string;
  start_date: string;
  end_date: string;
  today: string;
  total_questions: number;
  active_days: number;
  days: PracticeActivityDay[];
}

export interface PracticeSessionRecordsResponse {
  session_id: number;
  total_score: number;
  completed_at: string | null;
  question_count?: number;
  records: PracticeRecord[];
}

export type PracticeSessionSize = 5 | 10 | 15;

export async function startPracticeSession(
  category: string | undefined,
  count: PracticeSessionSize
): Promise<PracticeStartResponse> {
  const params: Record<string, string | number> = { count };
  if (category) params.category = category;
  const { data } = await apiClient.post<PracticeStartResponse>("/api/practice/sessions/start", null, { params });
  return data;
}

export async function startPracticeSessionCustom(questionIds: number[]): Promise<PracticeStartResponse> {
  const { data } = await apiClient.post<PracticeStartResponse>("/api/practice/sessions/start/custom", {
    question_ids: questionIds
  });
  return data;
}

export async function submitPracticeAnswer(
  sessionId: number,
  questionId: number,
  userAnswer: string
): Promise<PracticeSubmitResponse> {
  const { data } = await apiClient.post<PracticeSubmitResponse>(
    `/api/practice/sessions/${sessionId}/submit`,
    {
      question_id: questionId,
      user_answer: userAnswer
    },
    { timeout: 120000 }
  );
  return data;
}

export async function submitDailyPracticeAnswer(
  questionId: number,
  userAnswer: string
): Promise<PracticeSubmitResponse> {
  const { data } = await apiClient.post<PracticeSubmitResponse>("/api/practice/daily/submit", {
    question_id: questionId,
    user_answer: userAnswer
  }, { timeout: 120000 });
  return data;
}

export async function skipPracticeAnswer(
  sessionId: number,
  questionId: number
): Promise<PracticeSubmitResponse> {
  const { data } = await apiClient.post<PracticeSubmitResponse>(
    `/api/practice/sessions/${sessionId}/skip`,
    { question_id: questionId }
  );
  return data;
}

export async function fetchPracticeSummary(sessionId: number): Promise<PracticeSummaryResponse> {
  const { data } = await apiClient.get<PracticeSummaryResponse>(`/api/practice/sessions/${sessionId}/summary`);
  return data;
}

export async function fetchPracticeSessions(): Promise<PracticeSessionListItem[]> {
  const { data } = await apiClient.get<PracticeSessionListItem[]>("/api/practice/sessions");
  return data;
}

export async function fetchPracticeActivity(): Promise<PracticeActivityResponse> {
  const { data } = await apiClient.get<PracticeActivityResponse>("/api/practice/activity");
  return data;
}

export async function fetchPracticeSessionRecords(sessionId: number): Promise<PracticeSessionRecordsResponse> {
  const { data } = await apiClient.get<PracticeSessionRecordsResponse>(`/api/practice/sessions/${sessionId}/records`);
  return data;
}

export async function fetchPracticeCategories(): Promise<PracticeCategoriesResponse> {
  const { data } = await apiClient.get<PracticeCategoriesResponse>("/api/practice/categories");
  return data;
}

