import { defineStore } from "pinia";
import { createQuestion, fetchQuestions, type CreateQuestionPayload, type Question } from "../api/questions";

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
    async loadQuestions() {
      this.loading = true;
      try {
        this.items = await fetchQuestions();
      } finally {
        this.loading = false;
      }
    },
    async addQuestion(payload: CreateQuestionPayload) {
      await createQuestion(payload);
      await this.loadQuestions();
    }
  }
});

