import { createRouter, createWebHistory } from "vue-router";

const EmptyView = { template: "<div></div>" };

const routes = [
  { path: "/", redirect: "/overview" },
  { path: "/overview", name: "overview", component: EmptyView },
  { path: "/story", name: "story", component: EmptyView },
  { path: "/types", name: "types", component: EmptyView },
  { path: "/trends", name: "trends", component: EmptyView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
