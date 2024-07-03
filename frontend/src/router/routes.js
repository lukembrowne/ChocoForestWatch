const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/LandingPage.vue') },
      { 
        path: 'map/:rasterId/:polygonSetId',
        name: 'map',
        component: () => import('pages/MapPage.vue'),
        props: true
      },
      {path: 'model-training', component: () => import('pages/ModelTraining.vue') }
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