import { createRouter, createWebHistory } from "vue-router";

import AnswerRecordsView from "../views/AnswerRecordsView.vue";
import HomeView from "../views/HomeView.vue";
import ImportView from "../views/ImportView.vue";
import KbCopilotView from "../views/KbCopilotView.vue";
import PracticeHistoryView from "../views/PracticeHistoryView.vue";
import PracticeView from "../views/PracticeView.vue";
import QuestionsView from "../views/QuestionsView.vue";
import TaxonomyView from "../views/TaxonomyView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/questions", name: "questions", component: QuestionsView },
    { path: "/categories", name: "categories", component: TaxonomyView },
    { path: "/roles", name: "roles", component: TaxonomyView },
    { path: "/import", name: "import", component: ImportView },
    { path: "/copilot", name: "copilot", component: KbCopilotView },
    { path: "/practice", name: "practice", component: PracticeView },
    { path: "/practice-history", name: "practice-history", component: PracticeHistoryView },
    { path: "/answer-records", name: "answer-records", component: AnswerRecordsView }
  ]
});

export default router;

