import { createRouter, createWebHistory } from 'vue-router'
import authService from '../services/auth'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'LoginForm',
    component: () => import('../components/auth/LoginForm.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password/:uid/:token',
    name: 'ResetPassword',
    component: () => import('../components/auth/ResetPasswordForm.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/projects'
      },
      {
        path: 'projects',
        name: 'Projects',
        component: MainLayout
      }
    ]
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('../pages/ErrorNotFound.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Navigation guard
router.beforeEach((to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const currentUser = authService.getCurrentUser();

  if (requiresAuth && !currentUser) {
    next('/login');
  } else if (to.path === '/login' && currentUser) {
    next('/projects');
  } else {
    next();
  }
});

export default router

// If you need to export routes separately, you can do so like this:
export { routes }