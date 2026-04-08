import { createRouter, createWebHistory } from "vue-router";

import CategoriesView from "../views/CategoriesView.vue";
import HomeView from "../views/HomeView.vue";
import ImportView from "../views/ImportView.vue";
import PracticeView from "../views/PracticeView.vue";
import QuestionsView from "../views/QuestionsView.vue";
import RolesView from "../views/RolesView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/questions", name: "questions", component: QuestionsView },
    { path: "/categories", name: "categories", component: CategoriesView },
    { path: "/roles", name: "roles", component: RolesView },
    { path: "/import", name: "import", component: ImportView },
    { path: "/practice", name: "practice", component: PracticeView }
  ]
});

export default router;

