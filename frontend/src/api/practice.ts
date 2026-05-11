import { apiClient } from "./client";
import type { Question } from "./questions";

const streamBaseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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

export type GradeStreamLine =
  | { type: "reasoning"; delta: string }
  | {
      type: "done";
      record: PracticeRecord;
      analysis: string;
      reference_answer: string;
      grading_reused?: boolean;
    }
  | { type: "error"; detail: string };

export interface PracticeSubmitResponse {
  record: PracticeRecord;
  analysis: string;
  reference_answer: string;
  /** 仅 daily/submit：时间窗内同题同答复用上条阅卷时为 true */
  grading_reused?: boolean;
}

export interface SessionDimension {
  key: string;
  label: string;
  score: number;
}

export interface SessionFeedback {
  summary_text: string;
  dimensions: SessionDimension[];
}

export interface PracticeSummaryResponse {
  session_id: number;
  total_score: number;
  record_ids: number[];
  completed_at: string | null;
  question_count?: number;
  feedback?: SessionFeedback | null;
  summary_pending?: boolean;
}

export interface PracticeSessionListItem {
  id: number;
  total_score: number;
  question_count?: number;
  completed_at: string | null;
  created_at: string;
  summary_done?: boolean;
}

export interface PracticeRecordFeedItem {
  id: number;
  session_id: number | null;
  question_id: number;
  question_stem: string;
  user_answer: string;
  ai_score: number;
  created_at: string;
}

export interface PracticeRecordFeedPage {
  total: number;
  page: number;
  page_size: number;
  items: PracticeRecordFeedItem[];
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

export type PracticeQuestionPool = "all" | "wrongbook";

export async function startPracticeSession(
  category: string | undefined,
  count: PracticeSessionSize,
  pool: PracticeQuestionPool = "all"
): Promise<PracticeStartResponse> {
  const params: Record<string, string | number> = { count, pool };
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

async function consumeGradeSubmitNdjsonStream(
  path: string,
  body: { question_id: number; user_answer: string },
  onReasoningDelta?: (delta: string) => void
): Promise<PracticeSubmitResponse> {
  const controller = new AbortController();
  const timeoutMs = 120000;
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${streamBaseURL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal
    });
  } finally {
    window.clearTimeout(timer);
  }
  if (!res.ok) {
    const text = await res.text();
    let msg = text || `HTTP ${res.status}`;
    try {
      const j = JSON.parse(text) as { detail?: unknown };
      if (typeof j.detail === "string") msg = j.detail;
      else if (j.detail != null) msg = JSON.stringify(j.detail);
    } catch {
      /* keep msg */
    }
    throw new Error(msg);
  }
  if (!res.body) {
    throw new Error("Empty response body");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let outcome: PracticeSubmitResponse | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const obj = JSON.parse(line) as GradeStreamLine;
      if (obj.type === "reasoning") {
        onReasoningDelta?.(obj.delta);
        continue;
      }
      if (obj.type === "error") {
        throw new Error(typeof obj.detail === "string" ? obj.detail : JSON.stringify(obj.detail));
      }
      if (obj.type === "done") {
        outcome = {
          record: obj.record,
          analysis: obj.analysis,
          reference_answer: obj.reference_answer,
          grading_reused: obj.grading_reused
        };
      }
    }
  }
  if (buffer.trim()) {
    const obj = JSON.parse(buffer) as GradeStreamLine;
    if (obj.type === "error") {
      throw new Error(typeof obj.detail === "string" ? obj.detail : JSON.stringify(obj.detail));
    }
    if (obj.type === "done") {
      outcome = {
        record: obj.record,
        analysis: obj.analysis,
        reference_answer: obj.reference_answer,
        grading_reused: obj.grading_reused
      };
    }
  }
  if (!outcome) {
    throw new Error("判题流未返回结果");
  }
  return outcome;
}

export async function submitPracticeAnswer(
  sessionId: number,
  questionId: number,
  userAnswer: string,
  onReasoningDelta?: (delta: string) => void
): Promise<PracticeSubmitResponse> {
  return consumeGradeSubmitNdjsonStream(
    `/api/practice/sessions/${sessionId}/submit-stream`,
    { question_id: questionId, user_answer: userAnswer },
    onReasoningDelta
  );
}

export async function submitDailyPracticeAnswer(
  questionId: number,
  userAnswer: string,
  onReasoningDelta?: (delta: string) => void
): Promise<PracticeSubmitResponse> {
  return consumeGradeSubmitNdjsonStream(
    "/api/practice/daily/submit-stream",
    { question_id: questionId, user_answer: userAnswer },
    onReasoningDelta
  );
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

export async function fetchPracticeRecordFeed(params: {
  page?: number;
  page_size?: number;
  shanghai_date?: string;
}): Promise<PracticeRecordFeedPage> {
  const { data } = await apiClient.get<PracticeRecordFeedPage>("/api/practice/records", { params });
  return data;
}

export async function fetchPracticeSessionRecords(sessionId: number): Promise<PracticeSessionRecordsResponse> {
  const { data } = await apiClient.get<PracticeSessionRecordsResponse>(`/api/practice/sessions/${sessionId}/records`);
  return data;
}

export async function fetchPracticeCategories(
  pool: PracticeQuestionPool = "all"
): Promise<PracticeCategoriesResponse> {
  const { data } = await apiClient.get<PracticeCategoriesResponse>("/api/practice/categories", {
    params: { pool }
  });
  return data;
}

export interface WrongbookPage {
  total: number;
  page: number;
  page_size: number;
  items: Question[];
}

export async function fetchWrongbookPage(params: {
  state?: "in" | "out" | "all";
  category?: string;
  page?: number;
  page_size?: number;
}): Promise<WrongbookPage> {
  const { data } = await apiClient.get<WrongbookPage>("/api/practice/wrongbook", { params });
  return data;
}

export async function addWrongbookManual(questionId: number): Promise<Question> {
  const { data } = await apiClient.post<Question>("/api/practice/wrongbook/manual", {
    question_id: questionId
  });
  return data;
}

