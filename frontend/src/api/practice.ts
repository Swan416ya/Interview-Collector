import { apiClient } from "./client";
import type { Question } from "./questions";

export interface PracticeStartResponse {
  session_id: number;
  questions: Question[];
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
}

export interface PracticeSessionListItem {
  id: number;
  total_score: number;
  completed_at: string | null;
  created_at: string;
}

export interface PracticeSessionRecordsResponse {
  session_id: number;
  total_score: number;
  completed_at: string | null;
  records: PracticeRecord[];
}

export async function startPracticeSession(): Promise<PracticeStartResponse> {
  const { data } = await apiClient.post<PracticeStartResponse>("/api/practice/sessions/start");
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

export async function fetchPracticeSummary(sessionId: number): Promise<PracticeSummaryResponse> {
  const { data } = await apiClient.get<PracticeSummaryResponse>(`/api/practice/sessions/${sessionId}/summary`);
  return data;
}

export async function fetchPracticeSessions(): Promise<PracticeSessionListItem[]> {
  const { data } = await apiClient.get<PracticeSessionListItem[]>("/api/practice/sessions");
  return data;
}

export async function fetchPracticeSessionRecords(sessionId: number): Promise<PracticeSessionRecordsResponse> {
  const { data } = await apiClient.get<PracticeSessionRecordsResponse>(`/api/practice/sessions/${sessionId}/records`);
  return data;
}

