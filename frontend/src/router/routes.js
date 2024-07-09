const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/LandingPage.vue') },
      {
        path: 'map',
        name: 'map',
        component: () => import('pages/MapPage.vue'),
        props: route => ({ rasterId: route.query.rasterId, polygonSetId: route.query.polygonSetId })
      },
      {
        path: '/model-training/',
        name: 'ModelTraining',
        component: () => import('pages/ModelTraining.vue')
      },
      {
        path: '/prediction/',
        name: 'Prediction',
        component: () => import('pages/PredictionPage.vue')
      },
    ]
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue')
  }
]

export default routes