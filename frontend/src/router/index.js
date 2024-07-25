import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'  // Static import


const routes = [
  {
    path: '/',
    component: MainLayout,  // Use the imported component directly

  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('../pages/ErrorNotFound.vue'),
  },
];

export default function (/* { store } */) {
  const router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes, 
    history: createWebHistory()
  })

  return router
}

// If you need to export routes separately, you can do so like this:
export { routes }