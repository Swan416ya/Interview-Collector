import { defineStore } from "pinia";
import {
  createQuestion,
  deleteQuestion,
  fetchQuestionsPage,
  updateQuestion,
  type CreateQuestionPayload,
  type Question,
  type QuestionFilters,
  type UpdateQuestionPayload
} from "../api/questions";

interface QuestionState {
  loading: boolean;
  items: Question[];
  total: number;
  page: number;
  pageSize: number;
}

export const useQuestionStore = defineStore("question", {
  state: (): QuestionState => ({
    loading: false,
    items: [],
    total: 0,
    page: 1,
    pageSize: 20
  }),
  actions: {
    async loadQuestions(filters?: QuestionFilters & { page?: number; page_size?: number }) {
      this.loading = true;
      try {
        const page = filters?.page ?? this.page;
        const pageSize = filters?.page_size ?? this.pageSize;
        const data = await fetchQuestionsPage({ ...(filters ?? {}), page, page_size: pageSize });
        this.items = data.items;
        this.total = data.total;
        this.page = data.page;
        this.pageSize = data.page_size;
      } finally {
        this.loading = false;
      }
    },
    async addQuestion(payload: CreateQuestionPayload) {
      await createQuestion(payload);
      await this.loadQuestions();
    },
    async editQuestion(id: number, payload: UpdateQuestionPayload) {
      await updateQuestion(id, payload);
      await this.loadQuestions();
    },
    async removeQuestion(id: number) {
      await deleteQuestion(id);
      await this.loadQuestions();
    }
  }
});

