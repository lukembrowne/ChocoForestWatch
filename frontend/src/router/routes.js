const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/HomePage.vue') },
      {
        path: '',
        component: () => import('components/ProjectWizard.vue'),
        children: [
          { 
            path: 'project-setup',
            component: () => import('pages/ProjectSetupPage.vue')
          },
          { 
            path: 'data-preparation',
            component: () => import('pages/DataPreparationPage.vue')
          },
          { 
            path: 'model-training',
            component: () => import('pages/ModelTrainingPage.vue')
          },
          { 
            path: 'prediction',
            component: () => import('pages/PredictionPage.vue')
          },
        ]
      }
    ],
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
];

export default routes;