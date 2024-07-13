import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        components: {
          default: () => import('pages/HomePage.vue'),
        }
      }, { path: 'training', component: () => import('pages/TrainingPage.vue') },
      { path: 'prediction', component: () => import('pages/PredictionPage.vue') },
      { path: 'analysis', component: () => import('pages/AnalysisPage.vue') },
      { path: 'debug', component: () => import('pages/DebugPage.vue') }, // Make sure this line is present
      { path: 'satellite-browser', component: () => import('pages/SatelliteImageBrowser.vue') }, // Add this line

    ],
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
]

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