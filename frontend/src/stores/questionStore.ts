import { defineStore } from "pinia";
import {
  createQuestion,
  deleteQuestion,
  fetchQuestions,
  updateQuestion,
  type CreateQuestionPayload,
  type Question,
  type QuestionFilters,
  type UpdateQuestionPayload
} from "../api/questions";

interface QuestionState {
  loading: boolean;
  items: Question[];
}

export const useQuestionStore = defineStore("question", {
  state: (): QuestionState => ({
    loading: false,
    items: []
  }),
  actions: {
    async loadQuestions(filters?: QuestionFilters) {
      this.loading = true;
      try {
        this.items = await fetchQuestions(filters);
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

