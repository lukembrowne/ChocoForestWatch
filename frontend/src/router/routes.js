const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/model-training' },
      { path: 'model-training', component: () => import('pages/ModelTraining.vue') },
      { path: 'prediction', component: () => import('pages/PredictionPage.vue') },
      { path: 'analysis', component: () => import('pages/AnalysisPage.vue') }
    ]
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes