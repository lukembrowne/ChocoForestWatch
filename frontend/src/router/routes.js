const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/upload' }, // Redirect to /upload by default
      { path: 'upload', component: () => import('components/UploadData.vue') },
      { path: 'draw', component: () => import('components/DrawPolygons.vue') },
      { path: 'review', component: () => import('components/ReviewPolygons.vue') },
      { path: 'train', component: () => import('components/TrainModel.vue') },
      { path: 'predict', component: () => import('components/PredictLandUse.vue') },
      { path: 'visualize', component: () => import('components/VisualizeResults.vue') }
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