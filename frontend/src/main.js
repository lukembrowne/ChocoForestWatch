import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { Quasar } from 'quasar'
import quasarUserOptions from './quasar-user-options'
import routes from './router/routes'
import App from './App.vue'

import 'quasar/src/css/index.sass'

const router = createRouter({
  history: createWebHistory(),
  routes: routes // Make sure this is correct
})

const app = createApp(App)

app.use(Quasar, quasarUserOptions)
app.use(router)

app.mount('#app')